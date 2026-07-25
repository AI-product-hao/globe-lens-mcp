"""GlobeLens MCP server: website i18n / SEO audit tools for AI coding agents.

Exposes three tools that an AI assistant (Claude, Codex, Cursor, Cline, …) can
call to audit a public URL for internationalization and SEO readiness.
"""
from __future__ import annotations

import httpx
from dataclasses import asdict
from fastmcp import FastMCP

from .analyzer import analyze_html, robots_sitemap_urls

mcp = FastMCP("GlobeLens")

# Cap the HTML we feed to the parser. Real-world pages can be many MBs (heavy
# SPAs, inlined data); auditing that much is slow and rarely useful, so we
# truncate and tell the agent the result is partial.
MAX_HTML_BYTES = 2 * 1024 * 1024


def _decode_response(resp: httpx.Response) -> tuple[str, bool]:
    """Decode a response body to text safely and report if it was truncated.

    - Respects the response encoding (from Content-Type), falling back to UTF-8.
    - Never raises on a bad/unknown encoding: undecodable bytes become U+FFFD.
    - Truncates oversized bodies so the analyzer stays fast and bounded.
    """
    content = resp.content
    truncated = False
    if len(content) > MAX_HTML_BYTES:
        content = content[:MAX_HTML_BYTES]
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


@mcp.tool()
async def audit_url(
    url: str,
    timeout: int = 20,
    user_agent: str | None = None,
    verify_ssl: bool = True,
) -> dict:
    """Audit a public URL for SEO & internationalization readiness.

    Checks title, meta description, html lang, hreflang alternates, OG/Twitter
    cards, canonical, viewport, charset, H1 structure, image alt coverage, plus
    robots.txt / sitemap.xml presence. Returns a structured report with a 0-100
    score and prioritized issues.

    Args:
        url: The page to audit.
        timeout: Request timeout in seconds (default 20).
        user_agent: Override the default User-Agent (e.g. to mimic a real
            browser or a specific crawler).
        verify_ssl: Set False to skip TLS verification (useful for staging
            environments using self-signed certificates).
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
        try:
            resp = await client.get(url)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            return _http_error_result(
                url, e.response.status_code,
                f"HTTP {e.response.status_code} returned by {url}.")
        except httpx.HTTPError as e:
            return _http_error_result(url, None, f"Request to {url} failed: {e}")
        text, truncated = _decode_response(resp)
        report = analyze_html(text, url, truncated=truncated)
        robots_url, sitemap_url = robots_sitemap_urls(url)
        try:
            r = await client.get(robots_url)
            report.has_robots_txt = r.status_code == 200
        except Exception:
            report.has_robots_txt = None
        try:
            s = await client.get(sitemap_url)
            report.has_sitemap = s.status_code == 200
        except Exception:
            report.has_sitemap = None
        return report.to_dict()


@mcp.tool()
async def check_i18n(
    url: str,
    timeout: int = 20,
    user_agent: str | None = None,
    verify_ssl: bool = True,
) -> dict:
    """Focused check of internationalization signals: html lang, hreflang alternates, x-default.

    Args:
        url: The page to check.
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
        try:
            resp = await client.get(url)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            return _http_error_result(
                url, e.response.status_code,
                f"HTTP {e.response.status_code} returned by {url}.")
        except httpx.HTTPError as e:
            return _http_error_result(url, None, f"Request to {url} failed: {e}")
        text, truncated = _decode_response(resp)
        report = analyze_html(text, url, truncated=truncated)
        issues = [asdict(i) for i in report.issues
                  if i.code.startswith("hreflang") or i.code == "lang_missing"]
        return {
            "url": url,
            "html_lang": report.html_lang,
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
