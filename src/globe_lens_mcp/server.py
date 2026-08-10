"""GlobeLens MCP server: website i18n / SEO audit tools for AI coding agents.

Exposes three tools that an AI assistant (Claude, Codex, Cursor, Cline, …) can
call to audit a public URL for internationalization and SEO readiness.
"""
from __future__ import annotations

import re

import httpx
from dataclasses import asdict
from typing import Any
from urllib.parse import urljoin, urlparse

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


# How much of a probe response we sniff to decide what it actually is.
# robots.txt / sitemap.xml reveal themselves in the first few hundred bytes.
PROBE_SNIFF_BYTES = 2048

_HTML_CONTENT_TYPES = {"text/html", "application/xhtml+xml"}
_HTML_MARKERS = ("<!doctype html", "<html", "<head", "<body")
_SITEMAP_ROOTS = ("<urlset", "<sitemapindex")


def _content_type(resp: httpx.Response) -> str:
    """Bare content type of a response, lowercased, without parameters."""
    return resp.headers.get("content-type", "").split(";")[0].strip().lower()


def _body_head(resp: httpx.Response, limit: int = PROBE_SNIFF_BYTES) -> str:
    """First bytes of a body, decoded leniently — enough to sniff a format."""
    return resp.content[:limit].decode("utf-8", errors="replace").lstrip("\ufeff \t\r\n")


def _is_html_response(resp: httpx.Response) -> bool:
    """True when a response is an HTML document (by content type or by body).

    Used to unmask *soft* responses: SPA hosts (Vercel, Netlify, Cloudflare
    Pages, any catch-all rewrite) answer 200 with index.html for every unknown
    path, so /robots.txt and /sitemap.xml look like they exist when they do
    not.
    """
    if _content_type(resp) in _HTML_CONTENT_TYPES:
        return True
    return _body_head(resp)[:512].lower().startswith(_HTML_MARKERS)


def _is_robots_txt(resp: httpx.Response) -> bool:
    """True when a probe response is plausibly a real robots.txt.

    Deliberately lenient in the safe direction: any non-HTML 200 counts, so an
    *empty* robots.txt (valid, means "allow all") is still reported as present.
    Only an HTML body — the SPA fallback page — is rejected.
    """
    return resp.status_code == 200 and not _is_html_response(resp)


def _is_sitemap_xml(resp: httpx.Response) -> bool:
    """True when a probe response is plausibly a real sitemap.

    Requires an XML sitemap root (`<urlset>` or `<sitemapindex>`) or at least
    an XML content type. A sitemap always declares one of those roots, so this
    stays precise while rejecting the HTML fallback page.
    """
    if resp.status_code != 200 or _is_html_response(resp):
        return False
    head = _body_head(resp).lower()
    if any(root in head for root in _SITEMAP_ROOTS):
        return True
    return _content_type(resp).endswith("xml")


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


# The only schemes these tools can audit. Anything else is either not a web
# page at all (mailto:, tel:, javascript:) or not fetchable over HTTP
# (file:, data:, ftp:).
AUDITABLE_SCHEMES = ("http", "https")

# "localhost:3000" / "example.com:8080/x" parse as scheme="localhost" with
# path="3000" — a host:port that is missing its scheme, not an exotic
# protocol. The digits-first path is what distinguishes it from a genuine
# non-web scheme such as "data:text/html,..." or "mailto:a@b.c".
_PORT_LIKE_RE = re.compile(r"^\d+($|[/?#])")


def _invalid_url_result(url: str, message: str, suggestion: str | None) -> dict:
    """Agent-friendly payload for a URL the tool cannot even attempt to fetch.

    Same shape as `_http_error_result` (so callers branch on `ok` exactly
    once) plus a `suggestion`: when the input is a recognisable typo — most
    often a bare host with no scheme — we hand back the corrected string so
    the agent can retry in a single step instead of guessing at the wording
    of an error message.
    """
    return {
        "ok": False,
        "url": url,
        "status_code": None,
        "error": message,
        "suggestion": suggestion,
    }


def _url_input_error(url: str) -> dict | None:
    """Validate a caller-supplied URL; return an error payload, or None if OK.

    Checked *before* any socket is opened, because a bad URL is a caller-side
    mistake and dialling it out first only wastes a request (and, behind a
    proxy, produces a misleading transport error such as "Server disconnected"
    that looks like the site is down).

    The messages are deliberately specific about *which* thing is wrong: the
    HTTP client reports every one of these cases as "Request URL is missing an
    'http://' or 'https://' protocol", which is plainly wrong for something
    like `file:///etc/passwd` and sends an agent off to "fix" it by prefixing
    a scheme it already has.
    """
    raw = url.strip() if isinstance(url, str) else ""
    if not raw:
        return _invalid_url_result(
            url, "No URL was provided; pass an absolute http(s) URL, "
                 "e.g. https://example.com.", None)
    try:
        parsed = urlparse(raw)
    except ValueError as e:
        # e.g. "http://[" raises "Invalid IPv6 URL" straight out of urlparse.
        return _invalid_url_result(
            url, f"URL could not be parsed ({e}); pass an absolute http(s) "
                 f"URL, e.g. https://example.com.", None)

    scheme = parsed.scheme.lower()
    scheme_missing = not scheme or (
        "://" not in raw and bool(_PORT_LIKE_RE.match(parsed.path or ""))
    )
    if scheme_missing:
        # Strip a protocol-relative prefix ("//example.com") before suggesting.
        return _invalid_url_result(
            url, "URL has no scheme; prefix it with https:// (or http://).",
            f"https://{raw.lstrip('/')}")
    if scheme not in AUDITABLE_SCHEMES:
        return _invalid_url_result(
            url, f"Unsupported URL scheme '{scheme}'; only "
                 f"{' and '.join(AUDITABLE_SCHEMES)} pages can be audited.",
            None)
    if not parsed.netloc:
        return _invalid_url_result(
            url, "URL has no host; write the full origin, "
                 "e.g. https://example.com/page.", None)
    if any(ch.isspace() for ch in parsed.netloc):
        return _invalid_url_result(
            url, f"URL host '{parsed.netloc}' contains whitespace; "
                 f"percent-encode it or remove the stray space.", None)
    return None


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

    A URL that cannot be fetched at all (no scheme, no host, unsupported
    scheme, unparseable) is rejected up front with ok=false, a specific
    error, and a `suggestion` holding the corrected URL when one is obvious.
    """
    bad_url = _url_input_error(url)
    if bad_url:
        return bad_url
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
        except httpx.InvalidURL as e:
            # Not a subclass of httpx.HTTPError, so without this arm a URL the
            # client rejects would escape as an unhandled exception — exactly
            # the stack-trace-instead-of-result failure mode we removed
            # everywhere else.
            return _invalid_url_result(
                url, f"URL rejected by the HTTP client: {e}", None)
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
        # A 200 alone is not proof: catch-all SPA rewrites serve index.html for
        # both paths, so we also check the response really looks like the file.
        try:
            r = await client.get(robots_url, follow_redirects=True)
            report.has_robots_txt = _is_robots_txt(r)
        except Exception:
            report.has_robots_txt = None
        try:
            s = await client.get(sitemap_url, follow_redirects=True)
            report.has_sitemap = _is_sitemap_xml(s)
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
    (value validity, x-default, self-reference, and cluster integrity — one
    code pointing at several URLs, or several codes claiming one URL), and
    whether `<html lang>` agrees with the page's own hreflang entry.

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

    Unfetchable URLs are rejected up front (see audit_url).
    """
    bad_url = _url_input_error(url)
    if bad_url:
        return bad_url
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
        except httpx.InvalidURL as e:
            # Not a subclass of httpx.HTTPError, so without this arm a URL the
            # client rejects would escape as an unhandled exception — exactly
            # the stack-trace-instead-of-result failure mode we removed
            # everywhere else.
            return _invalid_url_result(
                url, f"URL rejected by the HTTP client: {e}", None)
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
            "hreflang_conflicts": report.hreflang_conflicts,
            "hreflang_duplicate_urls": report.hreflang_duplicate_urls,
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

    A 200 response is not taken as proof on its own: hosts with a catch-all
    rewrite (Vercel, Netlify, Cloudflare Pages, most SPA deployments) answer
    200 with index.html for any unknown path, so the body is sniffed to
    confirm it really is a robots.txt / sitemap rather than the fallback page.

    `found` is True/False when the answer is known, and None when the probe
    itself failed (DNS, TLS, timeout) — a network error means "unknown", not
    "missing". A URL the tool cannot fetch at all is reported as ok=false
    instead, so a caller-side typo is never dressed up as two "unknown"
    probes that look like a site outage.

    Args:
        url: The site (or any page on it) to check.
        timeout: Request timeout in seconds (default 20).
        user_agent: Override the default User-Agent.
        verify_ssl: Set False to skip TLS verification (e.g. staging sites).
    """
    bad_url = _url_input_error(url)
    if bad_url:
        return bad_url
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
        out: dict[str, Any] = {}
        try:
            r = await client.get(robots_url)
            out["robots_txt"] = {
                "url": robots_url,
                "found": _is_robots_txt(r),
                "status_code": r.status_code,
            }
        except Exception as e:  # noqa: BLE001
            # Unreachable != absent: claiming "missing" here would send the
            # agent off to create a file that may already exist.
            out["robots_txt"] = {"url": robots_url, "found": None, "error": str(e)}
        try:
            s = await client.get(sitemap_url)
            out["sitemap_xml"] = {
                "url": sitemap_url,
                "found": _is_sitemap_xml(s),
                "status_code": s.status_code,
            }
        except Exception as e:  # noqa: BLE001
            out["sitemap_xml"] = {"url": sitemap_url, "found": None, "error": str(e)}
        return out


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
