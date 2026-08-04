"""GlobeLens MCP server: website i18n / SEO audit tools for AI coding agents.

Exposes three tools that an AI assistant (Claude, Codex, Cursor, Cline, …) can
call to audit a public URL for internationalization and SEO readiness.
"""
from __future__ import annotations

import httpx
from dataclasses import asdict
from urllib.parse import urljoin

from fastmcp import FastMCP

from .analyzer import analyze_html, robots_sitemap_urls

mcp = FastMCP("GlobeLens")

# Cap the HTML we feed to the parser. Real-world pages can be many MBs (heavy
# SPAs, inlined data); auditing that much is slow and rarely useful, so we
# truncate and tell the agent the result is partial. The default can be
# overridden per call via the max_bytes tool parameter.
MAX_HTML_BYTES = 2 * 1024 * 1024

# Floor for a caller-supplied max_bytes. Below ~1 KiB there is not even room
# for a <head>, so the audit would be pure noise; we clamp instead of erroring
# to keep the tool call usable.
MIN_HTML_BYTES = 1024


def _effective_max_bytes(max_bytes: int | None) -> int:
    """Resolve the per-call HTML size cap: default when unset, floored else."""
    if max_bytes is None:
        return MAX_HTML_BYTES
    return max(MIN_HTML_BYTES, max_bytes)


def _decode_response(
    resp: httpx.Response, max_bytes: int = MAX_HTML_BYTES
) -> tuple[str, bool]:
    """Decode a response body to text safely and report if it was truncated.

    - Respects the response encoding (from Content-Type), falling back to UTF-8.
    - Never raises on a bad/unknown encoding: undecodable bytes become U+FFFD.
    - Truncates oversized bodies so the analyzer stays fast and bounded.
    """
    content = resp.content
    truncated = False
    if len(content) > max_bytes:
        content = content[:max_bytes]
        truncated = True
    encoding = resp.encoding or "utf-8"
    try:
        text = content.decode(encoding, errors="replace")
    except (LookupError, UnicodeDecodeError):
        text = content.decode("utf-8", errors="replace")
    return text, truncated


def _http_error_result(url: str, status_code: int | None, message: str) -> dict:
    """Agent-friendly failure payload for non-2xx or network errors.

    Previously a 404/500 or a DNS/timeout failure surfaced as an *unhandled
    exception* — the agent got a stack trace and no result at all. Now we
    return a small, parseable dict so an AI agent can react (retry, report, or
    skip the URL) instead of crashing the whole tool call.
    """
    return {
        "ok": False,
        "url": url,
        "status_code": status_code,
        "error": message,
    }


def _is_redirect(resp: httpx.Response) -> bool:
    """True for a 3xx response that actually carries a Location header.

    The header check matters: 304 Not Modified is a 3xx but is not a redirect,
    and a malformed 3xx without Location has nowhere to send us.
    """
    return 300 <= resp.status_code < 400 and "location" in resp.headers


def _redirect_stop_result(url: str, resp: httpx.Response) -> dict:
    """Report a redirect verbatim instead of following it.

    Returned when the caller passed follow_redirects=False and the server
    answered with a 3xx. There is no page body to audit, so instead of a
    useless empty report (or the HTTP error a bare raise_for_status would
    produce for a 3xx) we hand the agent exactly what it asked to see: the
    status code and the resolved target.
    """
    location = resp.headers.get("location", "")
    return {
        "ok": True,
        "url": url,
        "final_url": str(resp.url),
        "followed_redirects": False,
        "redirected": False,
        "status_code": resp.status_code,
        "redirect_to": urljoin(str(resp.url), location) if location else None,
        "note": (
            "Server returned a redirect and follow_redirects=false, so no page "
            "was analyzed. Audit the target directly, or re-run with "
            "follow_redirects=true to audit the destination page."
        ),
    }


@mcp.tool()
async def audit_url(
    url: str,
    timeout: int = 20,
    user_agent: str | None = None,
    verify_ssl: bool = True,
    max_bytes: int | None = None,
    follow_redirects: bool = True,
) -> dict:
    """Audit a public URL for SEO & internationalization readiness.

    Checks title, meta description, html lang, hreflang alternates, OG/Twitter
    cards, canonical, viewport, charset, H1 structure, image alt coverage,
    meta refresh redirects, plus robots.txt / sitemap.xml presence. Returns a
    structured report with a 0-100 score and prioritized issues.

    Redirects are followed by default; the report is computed against the final
    URL and includes final_url / redirected fields so the agent knows exactly
    which page was analyzed.

    Args:
        url: The page to audit.
        timeout: Request timeout in seconds (default 20).
        user_agent: Override the default User-Agent (e.g. to mimic a real
            browser or a specific crawler).
        verify_ssl: Set False to skip TLS verification (useful for staging
            environments using self-signed certificates).
        max_bytes: Cap on the HTML size fed to the parser (default 2 MiB).
            Raise it to fully audit heavy SPA pages, or lower it to keep
            audits of huge pages fast. Values below 1 KiB are clamped up;
            truncation is always flagged via page_truncated.
        follow_redirects: Set False to inspect the URL itself instead of the
            page it forwards to. Useful to verify a migration really returns
            301 (not 302) to the right target, or to see the language redirect
            on `/` rather than always landing on one locale. On a 3xx the tool
            then returns status_code + redirect_to instead of a page report.
    """
    headers = {
        "user-agent": user_agent
        or "GlobeLens/0.1 (+https://github.com/AI-product-hao/globe-lens-mcp)"
    }
    async with httpx.AsyncClient(
        follow_redirects=follow_redirects,
        timeout=timeout,
        headers=headers,
        verify=verify_ssl,
    ) as client:
        try:
            resp = await client.get(url)
            if not follow_redirects and _is_redirect(resp):
                return _redirect_stop_result(url, resp)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            return _http_error_result(
                url, e.response.status_code,
                f"HTTP {e.response.status_code} returned by {url}.")
        except httpx.HTTPError as e:
            return _http_error_result(url, None, f"Request to {url} failed: {e}")
        # Redirects are followed (http -> https, apex -> www, / -> /en/ ...),
        # so the body we analyze belongs to the *final* URL, not the requested
        # one. Analyzing against the requested URL would resolve relative
        # canonical/hreflang links against the wrong base, break the
        # self-referencing hreflang check, and probe robots.txt/sitemap.xml on
        # the wrong origin after a cross-host redirect.
        final_url = str(resp.url)
        redirected = bool(resp.history)
        text, truncated = _decode_response(resp, _effective_max_bytes(max_bytes))
        report = analyze_html(text, final_url, truncated=truncated)
        robots_url, sitemap_url = robots_sitemap_urls(final_url)
        # These probes always follow redirects, even when the page request did
        # not: crawlers follow robots.txt/sitemap.xml redirects too, so a site
        # that serves them via http -> https or apex -> www must not be
        # reported as "missing" just because the caller wanted to see the
        # page's own redirect.
        try:
            r = await client.get(robots_url, follow_redirects=True)
            report.has_robots_txt = r.status_code == 200
        except Exception:
            report.has_robots_txt = None
        try:
            s = await client.get(sitemap_url, follow_redirects=True)
            report.has_sitemap = s.status_code == 200
        except Exception:
            report.has_sitemap = None
        out = report.to_dict()
        out["url"] = url  # what the caller asked for, kept for traceability
        out["final_url"] = final_url
        out["redirected"] = redirected
        out["followed_redirects"] = follow_redirects
        return out


@mcp.tool()
async def check_i18n(
    url: str,
    timeout: int = 20,
    user_agent: str | None = None,
    verify_ssl: bool = True,
    max_bytes: int | None = None,
    follow_redirects: bool = True,
) -> dict:
    """Focused check of internationalization signals.

    Covers: `<html lang>` presence *and* BCP 47 validity, hreflang alternates
    (value validity, x-default, self-reference), and whether `<html lang>`
    agrees with the page's own hreflang entry.

    Args:
        url: The page to check.
        timeout: Request timeout in seconds (default 20).
        user_agent: Override the default User-Agent.
        verify_ssl: Set False to skip TLS verification (e.g. staging sites).
        max_bytes: Cap on the HTML size fed to the parser (default 2 MiB).
            Values below 1 KiB are clamped up; truncation is reported via the
            truncated flag in the result.
        follow_redirects: Set False to inspect the URL itself rather than the
            page it forwards to — e.g. to confirm that `/` really redirects to
            `/en/` for an English visitor instead of silently auditing one
            locale. On a 3xx the tool returns status_code + redirect_to.
    """
    headers = {
        "user-agent": user_agent
        or "GlobeLens/0.1 (+https://github.com/AI-product-hao/globe-lens-mcp)"
    }
    async with httpx.AsyncClient(
        follow_redirects=follow_redirects,
        timeout=timeout,
        headers=headers,
        verify=verify_ssl,
    ) as client:
        try:
            resp = await client.get(url)
            if not follow_redirects and _is_redirect(resp):
                return _redirect_stop_result(url, resp)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            return _http_error_result(
                url, e.response.status_code,
                f"HTTP {e.response.status_code} returned by {url}.")
        except httpx.HTTPError as e:
            return _http_error_result(url, None, f"Request to {url} failed: {e}")
        # Same as audit_url: analyze against the final (post-redirect) URL so
        # relative hreflang hrefs and the self-reference check use the page
        # the body actually came from.
        final_url = str(resp.url)
        redirected = bool(resp.history)
        text, truncated = _decode_response(resp, _effective_max_bytes(max_bytes))
        report = analyze_html(text, final_url, truncated=truncated)
        issues = [asdict(i) for i in report.issues
                  if i.code.startswith(("hreflang", "lang"))]
        return {
            "url": url,
            "final_url": final_url,
            "redirected": redirected,
            "followed_redirects": follow_redirects,
            "html_lang": report.html_lang,
            "lang_valid": report.lang_valid,
            "lang_hreflang_mismatch": report.lang_hreflang_mismatch,
            "hreflang": report.hreflang,
            "hreflang_self_ref": report.hreflang_self_ref,
            "issues": issues,
            "score": report.score,
            "truncated": truncated,
        }


@mcp.tool()
async def check_robots_sitemap(
    url: str,
    timeout: int = 20,
    user_agent: str | None = None,
    verify_ssl: bool = True,
) -> dict:
    """Check whether a site exposes robots.txt and sitemap.xml.

    Args:
        url: The site (or any page on it) to check.
        timeout: Request timeout in seconds (default 20).
        user_agent: Override the default User-Agent.
        verify_ssl: Set False to skip TLS verification (e.g. staging sites).
    """
    headers = {
        "user-agent": user_agent
        or "GlobeLens/0.1 (+https://github.com/AI-product-hao/globe-lens-mcp)"
    }
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=timeout,
        headers=headers,
        verify=verify_ssl,
    ) as client:
        robots_url, sitemap_url = robots_sitemap_urls(url)
        out: dict[str, any] = {}
        try:
            r = await client.get(robots_url)
            out["robots_txt"] = {"url": robots_url, "found": r.status_code == 200}
        except Exception as e:  # noqa: BLE001
            out["robots_txt"] = {"url": robots_url, "found": False, "error": str(e)}
        try:
            s = await client.get(sitemap_url)
            out["sitemap_xml"] = {"url": sitemap_url, "found": s.status_code == 200}
        except Exception as e:  # noqa: BLE001
            out["sitemap_xml"] = {"url": sitemap_url, "found": False, "error": str(e)}
        return out


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
