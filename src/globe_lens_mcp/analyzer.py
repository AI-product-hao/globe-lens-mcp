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
    h1_count: int = 0
    images_total: int = 0
    images_missing_alt: int = 0
    mixed_content: list[dict[str, str]] = field(default_factory=list)
    meta_robots: str | None = None
    has_json_ld: bool = False
    canonical: str | None = None
    canonical_url: str | None = None
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

    # Guard against degenerate input (None / empty / whitespace-only) so the
    # analyzer never crashes on a bad upstream response and returns a clear,
    # machine-readable signal instead.
    if not html or not str(html).strip():
        report.issues.append(Issue(
            "error", "empty_html",
            "Received empty or whitespace-only HTML; nothing to audit."))
        report.score = 0
        return report

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
            href = link.get("href")
            report.canonical = href
            report.canonical_url = urljoin(url, href)
        if "alternate" in rels and link.get("hreflang"):
            href = link.get("href")
            entry = {"hreflang": link.get("hreflang"), "href": href}
            if href:
                entry["abs_href"] = urljoin(url, href)
            report.hreflang.append(entry)

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

    # --- crawl / index control: meta robots ---
    meta_robots = soup.find("meta", attrs={"name": lambda v: v and v.lower() == "robots"})
    if meta_robots and meta_robots.get("content") and meta_robots["content"].strip():
        report.meta_robots = meta_robots["content"].strip()
        directives = [d.strip().lower() for d in report.meta_robots.split(",")]
        if "noindex" in directives:
            report.issues.append(Issue("warning", "robots_noindex",
                                       "Page is marked noindex; search engines will exclude it from results."))

    # --- structured data: JSON-LD ---
    json_ld = soup.find_all("script", attrs={"type": "application/ld+json"})
    report.has_json_ld = len(json_ld) > 0
    if not report.has_json_ld:
        report.issues.append(Issue("info", "json_ld_missing",
                                   "No JSON-LD structured data found; add schema.org markup for rich results."))

    # --- on-page structure: H1 ---
    h1_tags = soup.find_all("h1")
    report.h1_count = len(h1_tags)
    if report.h1_count == 0:
        report.issues.append(Issue("warning", "h1_missing",
                                    "No <h1> heading found; each page should have one main heading."))
    elif report.h1_count > 1:
        report.issues.append(Issue("warning", "h1_multiple",
                                    f"Found {report.h1_count} <h1> tags; use a single <h1> for clear document structure."))

    # --- on-page media: image alt text ---
    imgs = soup.find_all("img")
    report.images_total = len(imgs)
    report.images_missing_alt = sum(
        1 for img in imgs if not (img.get("alt") and str(img.get("alt")).strip())
    )
    if report.images_total > 0 and report.images_missing_alt > 0:
        report.issues.append(Issue(
            "warning", "images_missing_alt",
            f"{report.images_missing_alt} of {report.images_total} <img> tags missing alt text "
            f"(hurts accessibility and image SEO)."))

    # --- insecure subresources: mixed content on HTTPS pages ---
    # Browsers block/flag plaintext HTTP resources loaded from an HTTPS page;
    # these silently break rendering and erode user trust / SEO. Only flag when
    # the page itself is served over HTTPS (relative and protocol-relative URLs
    # such as "/x.png" or "//x.png" inherit HTTPS and are NOT mixed content).
    if urlparse(url).scheme == "https":
        for tag in soup.find_all(
            ["img", "script", "link", "iframe", "source", "audio", "video", "embed"]
        ):
            attr = "href" if tag.name == "link" else "src"
            val = tag.get(attr)
            if not isinstance(val, str):
                continue
            val = val.strip()
            if val.lower().startswith("http://"):
                report.mixed_content.append(
                    {"tag": tag.name, "attr": attr, "url": val}
                )
        if report.mixed_content:
            report.issues.append(Issue(
                "warning", "mixed_content",
                f"Found {len(report.mixed_content)} insecure HTTP subresource(s) on an "
                f"HTTPS page; browsers may block them and they hurt trust/SEO."))

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
