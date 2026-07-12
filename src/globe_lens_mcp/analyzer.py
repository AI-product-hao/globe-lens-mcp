"""Core SEO / internationalization analysis logic for GlobeLens.

This module is intentionally dependency-light (only beautifulsoup4) so it can
be unit-tested without any network access. Network fetching lives in server.py.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup


@dataclass
class Issue:
    severity: str  # "error" | "warning" | "info"
    code: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AuditReport:
    url: str
    title: str | None = None
    title_length: int = 0
    meta_description: str | None = None
    meta_description_length: int = 0
    html_lang: str | None = None
    charset: str | None = None
    viewport: bool = False
    canonical: str | None = None
    hreflang: list[dict[str, str]] = field(default_factory=list)
    og_tags: dict[str, str] = field(default_factory=dict)
    twitter_tags: dict[str, str] = field(default_factory=dict)
    has_robots_txt: bool | None = None
    has_sitemap: bool | None = None
    score: int = 0
    issues: list[Issue] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _rel_values(tag) -> list[str]:
    rel = tag.get("rel")
    if not rel:
        return []
    if isinstance(rel, str):
        return [rel.lower()]
    return [r.lower() for r in rel]


def analyze_html(html: str, url: str) -> AuditReport:
    """Parse raw HTML and produce an SEO / i18n audit report."""
    report = AuditReport(url=url)
    soup = BeautifulSoup(html, "html.parser")

    # --- <title> ---
    title_tag = soup.title
    if title_tag and title_tag.string and title_tag.string.strip():
        report.title = title_tag.string.strip()
        report.title_length = len(report.title)
        if report.title_length < 30:
            report.issues.append(Issue("warning", "title_short",
                                        f"Title is short ({report.title_length} chars); aim for 30-60."))
        elif report.title_length > 60:
            report.issues.append(Issue("warning", "title_long",
                                        f"Title is long ({report.title_length} chars); keep <= 60 for SERP."))
    else:
        report.issues.append(Issue("error", "title_missing", "Missing or empty <title> tag."))

    # --- meta description ---
    meta_desc = soup.find("meta", attrs={"name": lambda v: v and v.lower() == "description"})
    if meta_desc and meta_desc.get("content") and meta_desc["content"].strip():
        report.meta_description = meta_desc["content"].strip()
        report.meta_description_length = len(report.meta_description)
        if report.meta_description_length < 70:
            report.issues.append(Issue("warning", "desc_short", "Meta description is short (<70 chars)."))
        elif report.meta_description_length > 160:
            report.issues.append(Issue("warning", "desc_long",
                                        "Meta description exceeds 160 chars; may be truncated in SERP."))
    else:
        report.issues.append(Issue("warning", "desc_missing", "Missing meta description."))

    # --- <html lang> ---
    html_tag = soup.find("html")
    if html_tag and html_tag.get("lang") and html_tag["lang"].strip():
        report.html_lang = html_tag["lang"].strip()
    else:
        report.issues.append(Issue("error", "lang_missing",
                                    "Missing lang attribute on <html>; critical for internationalization."))

    # --- charset ---
    meta_charset = soup.find("meta", attrs={"charset": True})
    if meta_charset:
        report.charset = meta_charset.get("charset")
    else:
        report.issues.append(Issue("warning", "charset_missing", "No <meta charset> declared."))

    # --- viewport ---
    vp = soup.find("meta", attrs={"name": lambda v: v and v.lower() == "viewport"})
    report.viewport = vp is not None
    if not report.viewport:
        report.issues.append(Issue("warning", "viewport_missing",
                                    "Missing viewport meta tag (mobile unfriendly)."))

    # --- canonical / hreflang / og / twitter ---
    for link in soup.find_all("link"):
        rels = _rel_values(link)
        if "canonical" in rels and link.get("href"):
            report.canonical = link.get("href")
        if "alternate" in rels and link.get("hreflang"):
            report.hreflang.append({"hreflang": link.get("hreflang"), "href": link.get("href")})

    for meta in soup.find_all("meta"):
        prop = meta.get("property") or meta.get("name")
        content = meta.get("content")
        if not prop or content is None:
            continue
        pl = prop.lower()
        if pl.startswith("og:"):
            report.og_tags[pl] = content
        elif pl.startswith("twitter:"):
            report.twitter_tags[pl] = content

    if not report.hreflang:
        report.issues.append(Issue("info", "hreflang_missing",
                                    "No hreflang alternate links; needed for multi-region/multi-language SEO."))
    else:
        langs = [h["hreflang"].lower() for h in report.hreflang]
        if "x-default" not in langs:
            report.issues.append(Issue("warning", "hreflang_no_default",
                                        "No x-default hreflang; recommended for international sites."))

    if "og:title" not in report.og_tags or "og:description" not in report.og_tags:
        report.issues.append(Issue("info", "og_missing", "Missing Open Graph tags; weak social sharing preview."))

    # --- score ---
    penalty = {"error": 20, "warning": 8, "info": 3}
    score = 100
    for issue in report.issues:
        score -= penalty.get(issue.severity, 5)
    report.score = max(0, min(100, score))
    return report


def robots_sitemap_urls(url: str) -> tuple[str, str]:
    """Derive the canonical robots.txt and sitemap.xml URLs for a page URL."""
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    return urljoin(base, "/robots.txt"), urljoin(base, "/sitemap.xml")
