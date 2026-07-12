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


@mcp.tool()
async def audit_url(url: str) -> dict:
    """Audit a public URL for SEO & internationalization readiness.

    Checks title, meta description, html lang, hreflang alternates, OG/Twitter
    cards, canonical, viewport, charset, plus robots.txt / sitemap.xml presence.
    Returns a structured report with a 0-100 score and prioritized issues.
    """
    headers = {
        "user-agent": "GlobeLens/0.1 (+https://github.com/AI-product-hao/globe-lens-mcp)"
    }
    async with httpx.AsyncClient(follow_redirects=True, timeout=20, headers=headers) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        report = analyze_html(resp.text, url)
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
async def check_i18n(url: str) -> dict:
    """Focused check of internationalization signals: html lang, hreflang alternates, x-default."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        report = analyze_html(resp.text, url)
        issues = [asdict(i) for i in report.issues
                  if i.code.startswith("hreflang") or i.code == "lang_missing"]
        return {
            "url": url,
            "html_lang": report.html_lang,
            "hreflang": report.hreflang,
            "issues": issues,
            "score": report.score,
        }


@mcp.tool()
async def check_robots_sitemap(url: str) -> dict:
    """Check whether a site exposes robots.txt and sitemap.xml."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
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
