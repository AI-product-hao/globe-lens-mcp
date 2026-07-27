"""Core SEO / internationalization analysis logic for GlobeLens.

This module is intentionally dependency-light (only beautifulsoup4) so it can
be unit-tested without any network access. Network fetching lives in server.py.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup


# Rank used to order issues by importance. Higher = more urgent. This is the
# single source of truth for both the per-issue `priority` field and the global
# sort, so the two can never drift apart.
SEVERITY_RANK = {"error": 3, "warning": 2, "info": 1}

# Minimum body word count treated as "substantive" for SEO. Pages below this are
# flagged so an agent can recognize thin content (a known low-value signal that
# search engines demote). Kept as a module constant so it is easy to tune.
THIN_CONTENT_MIN_WORDS = 300

# Actionable, copy-paste-friendly fix hint per issue code. The `message` says
# *what* is wrong; `fix` says *what to do about it* — so an AI agent (or a
# human) can apply the remedy without first researching the rule. Kept as a
# single module-level table so message text and remedies never drift apart
# and adding a new issue code forces a conscious decision about its fix.
FIX_HINTS: dict[str, str] = {
    "empty_html": "Verify the URL returns an HTML document (check redirects, auth walls, and bot blocking).",
    "title_missing": "Add <title>Your page title</title> inside <head>; aim for 30-60 characters.",
    "title_short": "Expand the <title> to 30-60 characters including your primary keyword.",
    "title_long": "Shorten the <title> to 60 characters or less so it is not cut off in search results.",
    "desc_missing": 'Add <meta name="description" content="..."> with a 70-160 character summary.',
    "desc_short": "Expand the meta description to 70-160 characters to improve snippet quality.",
    "desc_long": "Trim the meta description to 160 characters or less to avoid SERP truncation.",
    "lang_missing": 'Add a lang attribute to the root element, e.g. <html lang="en">.',
    "charset_missing": 'Add <meta charset="utf-8"> as the first element inside <head>.',
    "viewport_missing": 'Add <meta name="viewport" content="width=device-width, initial-scale=1"> for mobile rendering.',
    "hreflang_missing": 'Add <link rel="alternate" hreflang="..." href="..."> for each language/region version of this page.',
    "hreflang_no_default": 'Add <link rel="alternate" hreflang="x-default" href="..."> pointing to the fallback version.',
    "hreflang_invalid": "Replace each invalid value with an ISO 639-1 language code, optionally plus a region (e.g. 'en', 'en-US'), or 'x-default'.",
    "hreflang_no_self_ref": "Add an hreflang link whose href is this page's own URL to the alternate set.",
    "og_missing": 'Add <meta property="og:title" ...> and <meta property="og:description" ...> for social sharing previews.',
    "robots_noindex": "Remove 'noindex' from the meta robots tag if this page should appear in search results.",
    "json_ld_missing": 'Add a <script type="application/ld+json"> block with schema.org markup matching the page type.',
    "h1_missing": "Add exactly one <h1> heading describing the page's main topic.",
    "h1_multiple": "Keep a single <h1> and demote the others to <h2>/<h3>.",
    "images_missing_alt": 'Add a descriptive alt="..." to each listed <img> (use alt="" only for purely decorative images).',
    "mixed_content": "Change each listed http:// subresource URL to https:// (or a relative/protocol-relative path).",
    "broken_anchors": "For each listed anchor, add the missing id to the target element or update the href to an existing id.",
    "thin_content": "Add substantive body text (aim for 300+ words) covering the page's topic in depth.",
    "page_truncated": "Re-audit critical sections separately, or reduce the page size (the audit only covers the first part).",
}

# A well-formed hreflang value is an ISO 639-1 language code (2-3 letters),
# optionally followed by a region: an ISO 3166-1 alpha-2 code (2 letters) or a
# UN M.49 area code (3 digits), joined by a hyphen. The value is case-insensitive
# and "x-default" is a reserved keyword. Anything else (e.g. the extremely common
# "en_US" with an underscore, or a full word like "english") is silently ignored
# by search engines — so it is worth surfacing to the author.
_HREFLANG_RE = re.compile(r"^[a-z]{2,3}(-[a-z]{2}|-[0-9]{3})?$", re.IGNORECASE)


def _is_valid_hreflang(code: str | None) -> bool:
    """Return True if `code` is a syntactically valid hreflang value."""
    if not code:
        return False
    code = code.strip()
    if code.lower() == "x-default":
        return True
    return bool(_HREFLANG_RE.match(code))


def _self_ref_key(u: str) -> tuple[str, str, str, str]:
    """Normalize a URL for self-reference comparison.

    Scheme/host are case-insensitive and a trailing slash on the path is not
    significant ("https://example.com" == "https://example.com/"), so we
    compare on a normalized tuple instead of raw string equality.
    """
    p = urlparse(u)
    path = p.path.rstrip("/") or "/"
    return (p.scheme.lower(), p.netloc.lower(), path, p.query)


@dataclass
class Issue:
    severity: str  # "error" | "warning" | "info"
    code: str
    message: str
    # Machine-sortable importance derived from `severity`. Added incrementally
    # (defaults to 0) so callers can trust the highest-priority item first.
    priority: int = 0
    # Actionable remedy derived from `code` (see FIX_HINTS). Filled in
    # automatically so every issue ships with a concrete "do this" step;
    # empty string only for unknown codes.
    fix: str = ""

    def __post_init__(self) -> None:
        if self.priority == 0:
            self.priority = SEVERITY_RANK.get(self.severity, 0)
        if not self.fix:
            self.fix = FIX_HINTS.get(self.code, "")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def sort_issues(issues: list[Issue]) -> list[Issue]:
    """Order issues by severity (most urgent first), then by code for stable,
    deterministic output so a caller can always trust `issues[0]` is the
    highest-priority fix to make.
    """
    return sorted(issues, key=lambda i: (-i.priority, i.code))


@dataclass
class AuditReport:
    url: str
    title: str | None = None
    title_length: int = 0
    meta_description: str | None = None
    meta_description_length: int = 0
    word_count: int = 0
    html_lang: str | None = None
    charset: str | None = None
    viewport: bool = False
    h1_count: int = 0
    images_total: int = 0
    images_missing_alt: int = 0
    broken_anchors: list[dict[str, str]] = field(default_factory=list)
    mixed_content: list[dict[str, str]] = field(default_factory=list)
    meta_robots: str | None = None
    has_json_ld: bool = False
    canonical: str | None = None
    canonical_url: str | None = None
    hreflang: list[dict[str, str]] = field(default_factory=list)
    invalid_hreflang: list[str] = field(default_factory=list)
    # None = page has no hreflang links (check not applicable);
    # True/False = whether the hreflang set references the page itself.
    hreflang_self_ref: bool | None = None
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


def analyze_html(html: str, url: str, truncated: bool = False) -> AuditReport:
    """Parse raw HTML and produce an SEO / i18n audit report.

    Args:
        html: The page HTML (decoded text).
        url: The page URL (used to resolve relative links).
        truncated: Set True when the HTML was cut off before analysis (e.g.
            an oversized page). Adds a `page_truncated` info issue so the agent
            knows the result may be incomplete.
    """
    report = AuditReport(url=url)

    # Guard against degenerate input (None / empty / whitespace-only) so the
    # analyzer never crashes on a bad upstream response and returns a clear,
    # machine-readable signal instead.
    if not html or not str(html).strip():
        report.issues.append(Issue(
            "error", "empty_html",
            "Received empty or whitespace-only HTML; nothing to audit."))
        report.score = 0
        report.issues = sort_issues(report.issues)
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
    # Two valid ways to declare the charset exist in the wild:
    #   1. HTML5:  <meta charset="utf-8">
    #   2. Legacy: <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    # The legacy form is still extremely common on older and non-English sites,
    # so only accepting form 1 produced a false "charset_missing" warning. We now
    # honour both and extract the charset value from the http-equiv content.
    meta_charset = soup.find("meta", attrs={"charset": True})
    if meta_charset and meta_charset.get("charset"):
        report.charset = meta_charset.get("charset").strip()
    else:
        http_equiv = soup.find(
            "meta",
            attrs={"http-equiv": lambda v: v and v.lower() == "content-type"},
        )
        content = http_equiv.get("content") if http_equiv else None
        if content:
            m = re.search(r"charset\s*=\s*([^\s;]+)", content, re.IGNORECASE)
            if m:
                report.charset = m.group(1).strip()
    if not report.charset:
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
        # Flag malformed hreflang values (e.g. "en_US" with an underscore, or a
        # full word like "english"). Search engines silently ignore invalid
        # codes, so the intended alternate is never picked up.
        report.invalid_hreflang = [
            h["hreflang"] for h in report.hreflang
            if not _is_valid_hreflang(h.get("hreflang"))
        ]
        if report.invalid_hreflang:
            report.issues.append(Issue(
                "warning", "hreflang_invalid",
                f"Invalid hreflang value(s): {', '.join(report.invalid_hreflang)}; "
                f"use an ISO language code optionally with a region "
                f"(e.g. 'en' or 'en-US') or 'x-default'."))
        # Self-referencing hreflang: Google requires every page in an hreflang
        # cluster to also list *itself* as one of the alternates. When the
        # self-reference is missing, search engines may ignore the whole set —
        # a silent failure that is very common on hand-maintained i18n sites.
        # Compare on normalized URLs (case-insensitive host, trailing slash
        # insensitive) using each entry's resolved absolute href.
        page_key = _self_ref_key(url)
        report.hreflang_self_ref = any(
            _self_ref_key(h.get("abs_href") or h.get("href") or "") == page_key
            for h in report.hreflang
        )
        if not report.hreflang_self_ref:
            report.issues.append(Issue(
                "warning", "hreflang_no_self_ref",
                "hreflang set does not reference this page itself; Google "
                "requires a self-referencing hreflang link, otherwise the "
                "whole cluster may be ignored."))

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

    # --- broken in-page anchor links ---
    # An in-page jump link (href="#fragment") that targets an id/name which does
    # not exist in the document looks fine in source but does nothing when
    # clicked — a real, common bug that hurts accessibility, internal-link SEO,
    # and UX. We collect every element id/name as a valid jump target and report
    # any anchor whose target is missing. (Pure HTML, no network — unlike full
    # cross-page link checking, which needs a crawl.)
    anchor_targets: set[str] = set()
    for el in soup.find_all(attrs={"id": True}):
        anchor_targets.add(str(el.get("id")))
    for el in soup.find_all(attrs={"name": True}):
        n = el.get("name")
        if isinstance(n, str):
            anchor_targets.add(n)
    seen_anchor: set[str] = set()
    for a in soup.find_all("a"):
        href = a.get("href")
        if not isinstance(href, str):
            continue
        href = href.strip()
        if not href.startswith("#"):
            continue
        frag = href[1:].strip()
        if not frag:
            # href="#" → scroll-to-top; a valid (if empty) target, not broken.
            continue
        if frag in anchor_targets or frag in seen_anchor:
            continue
        seen_anchor.add(frag)
        report.broken_anchors.append({
            "href": href,
            "text": (a.get_text() or "").strip()[:80],
        })
    if report.broken_anchors:
        report.issues.append(Issue(
            "warning", "broken_anchors",
            f"Found {len(report.broken_anchors)} in-page anchor link(s) pointing to a "
            f"missing #fragment target; they do nothing when clicked."))

    # --- content depth: thin-content / body word count ---
    # Search engines treat pages with very little original text as low-value
    # ("thin content"). We count *visible* body words, deliberately excluding
    # <script>/<style> boilerplate, so an agent can spot pages that need more
    # substance. Pure HTML, network-free, and non-mutating (we don't decompose
    # tags, so later checks are unaffected).
    body = soup.body or soup
    visible_text = " ".join(
        s
        for s in body.find_all(string=True)
        if s.parent is not None and s.parent.name not in ("script", "style")
    )
    report.word_count = len(re.split(r"\s+", visible_text.strip())) if visible_text.strip() else 0
    if report.word_count < THIN_CONTENT_MIN_WORDS:
        report.issues.append(Issue(
            "info", "thin_content",
            f"Page body has only {report.word_count} words (< {THIN_CONTENT_MIN_WORDS}); "
            f"consider adding more substantive content for SEO."))

    # --- partial-input signal: the page was truncated before analysis ---
    if truncated:
        report.issues.append(Issue(
            "info", "page_truncated",
            "Page exceeded the size limit and was truncated before analysis; "
            "results may be incomplete."))

    # --- score ---
    penalty = {"error": 20, "warning": 8, "info": 3}
    score = 100
    for issue in report.issues:
        score -= penalty.get(issue.severity, 5)
    report.score = max(0, min(100, score))
    # Return issues ordered by severity so callers (and AI agents) see the
    # highest-priority fixes first — the tool's "prioritized issues" promise.
    report.issues = sort_issues(report.issues)
    return report


def robots_sitemap_urls(url: str) -> tuple[str, str]:
    """Derive the canonical robots.txt and sitemap.xml URLs for a page URL."""
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    return urljoin(base, "/robots.txt"), urljoin(base, "/sitemap.xml")
