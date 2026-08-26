"""Core SEO / internationalization analysis logic for GlobeLens.

This module is intentionally dependency-light (only beautifulsoup4) so it can
be unit-tested without any network access. Network fetching lives in server.py.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any
from urllib.parse import unquote, urljoin, urlparse

from bs4 import BeautifulSoup


# Rank used to order issues by importance. Higher = more urgent. This is the
# single source of truth for both the per-issue `priority` field and the global
# sort, so the two can never drift apart.
SEVERITY_RANK = {"error": 3, "warning": 2, "info": 1}

# Minimum body word count treated as "substantive" for SEO. Pages below this are
# flagged so an agent can recognize thin content (a known low-value signal that
# search engines demote). Kept as a module constant so it is easy to tune.
THIN_CONTENT_MIN_WORDS = 300

# Some scripts do not separate words with spaces, so splitting on whitespace
# counts a whole article as one or two "words" and every such page gets falsely
# flagged as thin content. For those scripts we count characters and convert to
# an English-equivalent word count using the ratios below (the same rough
# convention the translation industry uses).
#   - Chinese / Japanese: ~1.7 characters per equivalent word.
#   - Thai: ~4.5 characters per word (an alphabetic, but space-free, script).
# Korean is NOT in this table on purpose: Hangul text *is* space-separated
# (eojeol), so the plain whitespace split already produces a sane count.
CJK_CHARS_PER_WORD = 1.7
THAI_CHARS_PER_WORD = 4.5

_CJK_RE = re.compile(
    "["
    "\u3040-\u30ff"  # Hiragana + Katakana
    "\u3400-\u4dbf"  # CJK Unified Ideographs Extension A
    "\u4e00-\u9fff"  # CJK Unified Ideographs
    "\uf900-\ufaff"  # CJK Compatibility Ideographs
    "\U00020000-\U0002a6df"  # CJK Unified Ideographs Extension B
    "]"
)
_THAI_RE = re.compile("[\u0e00-\u0e7f]")

# (pattern, characters-per-word) for every space-free script we handle.
_NO_SPACE_SCRIPTS: tuple[tuple[re.Pattern[str], float], ...] = (
    (_CJK_RE, CJK_CHARS_PER_WORD),
    (_THAI_RE, THAI_CHARS_PER_WORD),
)


def _count_words(text: str) -> int:
    """Count words in a way that also works for space-free scripts.

    Latin-style text is split on whitespace as usual; characters belonging to
    scripts that do not use spaces (Chinese, Japanese, Thai) are counted and
    converted to an equivalent word count. Mixed-language pages add up both
    parts, so a bilingual page is measured fairly.
    """
    if not text or not text.strip():
        return 0
    total = 0.0
    remainder = text
    for pattern, chars_per_word in _NO_SPACE_SCRIPTS:
        matched = pattern.findall(remainder)
        if matched:
            total += len(matched) / chars_per_word
            # Replace with a space so neighbouring Latin words stay separated.
            remainder = pattern.sub(" ", remainder)
    remainder = remainder.strip()
    if remainder:
        # Ignore leftover tokens that carry no letters or digits: CJK sentences
        # leave their punctuation behind ("。", "、"), and navigation separators
        # ("|", "-", "•") are not content in any language.
        total += sum(
            1
            for token in re.split(r"\s+", remainder)
            if any(ch.isalnum() for ch in token)
        )
    return int(round(total))

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
    "title_duplicate": "Keep exactly one <title> element in <head>; browsers only use the first, so the extra title(s) are silently ignored (a duplicated title is almost always a templating bug).",
    "desc_missing": 'Add <meta name="description" content="..."> with a 70-160 character summary.',
    "desc_short": "Expand the meta description to 70-160 characters to improve snippet quality.",
    "desc_long": "Trim the meta description to 160 characters or less to avoid SERP truncation.",
    "desc_duplicate": 'Keep exactly one <meta name="description">; remove the duplicates injected by plugins/CMS so search engines use your chosen snippet.',
    "lang_missing": 'Add a lang attribute to the root element, e.g. <html lang="en">.',
    "lang_invalid": "Replace the <html lang> value with a BCP 47 tag: language, optional script/region joined by hyphens (e.g. 'en', 'en-US', 'zh-Hans').",
    "lang_hreflang_mismatch": "Make <html lang> match the language of this page's own hreflang entry (change whichever one is wrong).",
    "charset_missing": 'Add <meta charset="utf-8"> as the first element inside <head>.',
    "viewport_missing": 'Add <meta name="viewport" content="width=device-width, initial-scale=1"> for mobile rendering.',
    "viewport_zoom_disabled": 'Remove user-scalable="no" and any maximum-scale<=1 from the viewport meta (e.g. width=device-width, initial-scale=1) so low-vision users can zoom the page.',
    "hreflang_missing": 'Add <link rel="alternate" hreflang="..." href="..."> for each language/region version of this page.',
    "hreflang_no_default": 'Add <link rel="alternate" hreflang="x-default" href="..."> pointing to the fallback version.',
    "hreflang_invalid": "Replace each invalid value with an ISO 639-1 language code, optionally plus a region (e.g. 'en', 'en-US'), or 'x-default'.",
    "hreflang_no_self_ref": "Add an hreflang link whose href is this page's own URL to the alternate set.",
    "hreflang_conflict": "Declare each hreflang value exactly once: delete the duplicate <link rel=\"alternate\"> tags, or fix the language code on whichever one points at the wrong URL.",
    "hreflang_duplicate_url": "Give each language its own URL, or drop the extra hreflang values so one URL is not claimed by several languages (only x-default may share a URL).",
    "og_missing": 'Add <meta property="og:title" ...> and <meta property="og:description" ...> for social sharing previews.',
    "robots_noindex": "Remove 'noindex' from the meta robots tag if this page should appear in search results.",
    "json_ld_missing": 'Add a <script type="application/ld+json"> block with schema.org markup matching the page type.',
    "h1_missing": "Add exactly one <h1> heading describing the page's main topic.",
    "h1_multiple": "Keep a single <h1> and demote the others to <h2>/<h3>.",
    "images_missing_alt": 'Add a descriptive alt="..." to each listed <img> (use alt="" only for purely decorative images).',
    "images_missing_dims": 'Add width="..." height="..." (or set aspect-ratio in CSS) to each listed <img> so the browser reserves space and avoids layout shift (CLS) as images load.',
    "mixed_content": "Change each listed http:// subresource URL to https:// (or a relative/protocol-relative path).",
    "broken_anchors": "For each listed anchor, add the missing id to the target element or update the href to an existing id.",
    "thin_content": "Add substantive body text (aim for 300+ words) covering the page's topic in depth.",
    "page_truncated": "Re-audit critical sections separately, or reduce the page size (the audit only covers the first part).",
    "canonical_conflict": "Keep a single canonical link pointing to one URL; remove the duplicates or make them all agree on the same address.",
    "meta_refresh_redirect": 'Replace the <meta http-equiv="refresh"> tag with a real server-side redirect (301 for permanent, 302 for temporary).',
    "meta_refresh_reload": 'Remove the timed <meta http-equiv="refresh">; refresh the data with JavaScript instead and give users a way to pause or extend it.',
    "unsafe_blank_link": 'Add rel="noopener noreferrer" to every external <a target="_blank"> link (or drop target="_blank"); otherwise the opened page can hijack window.opener.',
    "favicon_missing": 'Add <link rel="icon" href="/favicon.ico"> (and an apple-touch-icon for iOS) to <head> so the page shows a brand icon in tabs, bookmarks and search results.',
    "og_empty": 'Fill in a non-empty content value for the listed Open Graph tag(s), e.g. <meta property="og:title" content="Page title">; an empty value is ignored by social platforms and your share preview falls back unpredictably.',
    "og_image_missing": 'Add <meta property="og:image" content="https://.../social-card.png"> (1200x630 works best across platforms) so shared links show a thumbnail; a text-only preview is clicked far less often.',
}

# <meta http-equiv="refresh" content="..."> payloads seen in the wild:
#   "0; url=/en/"      "5"      "0;URL='https://example.com/'"      "url=/en/"
# The delay is a non-negative integer per the HTML spec, the separator and the
# quotes around the target are both optional, and everything is case-
# insensitive. Content that does not match this shape (e.g. junk text) is
# deliberately ignored rather than guessed at, so we never invent a redirect.
_META_REFRESH_RE = re.compile(
    r"^\s*(?P<delay>\d+)?\s*[;,]?\s*(?:url\s*=\s*(?P<url>.+?))?\s*$",
    re.IGNORECASE,
)

# A well-formed language tag (BCP 47, as used by both `<html lang>` and
# hreflang) is an ISO 639-1/639-2 language code (2-3 letters), optionally
# followed by an ISO 15924 script (4 letters, e.g. "Hans"), optionally followed
# by a region: an ISO 3166-1 alpha-2 code (2 letters) or a UN M.49 area code
# (3 digits). Subtags are hyphen-joined and case-insensitive. Anything else
# (e.g. the extremely common "en_US" with an underscore, or a full word like
# "english") is silently ignored by browsers and search engines — so it is
# worth surfacing to the author.
_LANG_TAG_RE = re.compile(
    r"^[a-z]{2,3}(-[a-z]{4})?(-([a-z]{2}|[0-9]{3}))?$", re.IGNORECASE
)


def _is_valid_language_tag(code: str | None) -> bool:
    """Return True if `code` is a syntactically valid BCP 47 language tag."""
    if not code:
        return False
    return bool(_LANG_TAG_RE.match(code.strip()))


def _is_valid_hreflang(code: str | None) -> bool:
    """Return True if `code` is a syntactically valid hreflang value.

    Same grammar as `<html lang>` plus the reserved "x-default" keyword.
    """
    if not code:
        return False
    if code.strip().lower() == "x-default":
        return True
    return _is_valid_language_tag(code)


def _primary_subtag(code: str | None) -> str:
    """Return the lowercase language subtag of a tag ("en-GB" -> "en")."""
    if not code:
        return ""
    return code.strip().split("-", 1)[0].lower()


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


def tally_issues(issues: list[Issue]) -> dict[str, int]:
    """Count issues by severity.

    Returns a complete ``{"error": n, "warning": n, "info": n}`` breakdown,
    always with all three keys present (zero-filled). A caller — an agent, a
    CI gate or a dashboard — can read the page's health at a glance from this
    summary without iterating the (potentially long) ``issues`` list, and can
    write rules like "fail when warning_count > N" without re-parsing every
    item. It is the same data the report already carries, just pre-aggregated,
    so the two can never drift apart.
    """
    counts = {"error": 0, "warning": 0, "info": 0}
    for issue in issues:
        if issue.severity in counts:
            counts[issue.severity] += 1
    return counts


@dataclass
class AuditReport:
    url: str
    title: str | None = None
    title_length: int = 0
    meta_description: str | None = None
    meta_description_length: int = 0
    # Number of <meta name="description"> tags found. 0 = absent, 1 = the normal
    # case, >1 = duplicate declarations (CMS/plugin injection) that make search
    # engines pick one arbitrarily, diluting the controlled SERP snippet.
    meta_description_count: int = 0
    word_count: int = 0
    html_lang: str | None = None
    # None = no lang attribute (check not applicable); True/False = whether the
    # declared value is a syntactically valid BCP 47 language tag.
    lang_valid: bool | None = None
    # None = not applicable (no lang, or no self-referencing language-specific
    # hreflang to compare against); True = <html lang> and the page's own
    # hreflang entry declare different languages.
    lang_hreflang_mismatch: bool | None = None
    charset: str | None = None
    viewport: bool = False
    # False = viewport present without disabling zoom; True = the viewport
    # meta locks user zoom (user-scalable=no / maximum-scale<=1), a WCAG 2.5.1
    # failure that traps low-vision users at 100% (None is never used: when the
    # viewport is absent we raise viewport_missing instead and leave this False).
    viewport_zoom_disabled: bool = False
    h1_count: int = 0
    images_total: int = 0
    images_missing_alt: int = 0
    # Number of <img> tags with no explicit `width` / `height` attribute.
    # Without them the browser cannot reserve space, so every image shifts the
    # page layout (Cumulative Layout Shift) as it streams in — a Core Web
    # Vitals concern that hurts perceived stability and, on image-heavy pages,
    # real search rankings. Reported (info, cheap fix) so an agent can pre-empt
    # the shift alongside accessibility work.
    images_missing_dims: int = 0
    broken_anchors: list[dict[str, str]] = field(default_factory=list)
    # External <a target="_blank"> links that open a new tab without
    # rel="noopener noreferrer": they leak window.opener (reverse tabnabbing)
    # and waste resources. Each entry carries the raw href and visible text.
    unsafe_blank_links: list[dict[str, str]] = field(default_factory=list)
    mixed_content: list[dict[str, str]] = field(default_factory=list)
    meta_robots: str | None = None
    # Raw content of <meta http-equiv="refresh"> when present, plus its parsed
    # parts: delay in seconds, and the absolute redirect target (None when the
    # tag has no url= and therefore just reloads the page itself).
    meta_refresh: str | None = None
    meta_refresh_delay: int | None = None
    meta_refresh_url: str | None = None
    has_json_ld: bool = False
    # False = no favicon <link> found (check not applicable only on feeds/docs
    # with no browser representation; for a normal HTML page it is a miss).
    has_favicon: bool = False
    canonical: str | None = None
    canonical_url: str | None = None
    # All distinct canonical URLs declared on the page (absolute form). Empty
    # when there is no canonical link; >1 entry signals a conflicting/duplicate
    # canonical set that search engines will ignore.
    canonical_urls: list[str] = field(default_factory=list)
    hreflang: list[dict[str, str]] = field(default_factory=list)
    invalid_hreflang: list[str] = field(default_factory=list)
    # None = page has no hreflang links (check not applicable);
    # True/False = whether the hreflang set references the page itself.
    hreflang_self_ref: bool | None = None
    # Language codes declared more than once with *different* targets, e.g.
    # [{"hreflang": "de", "urls": ["https://x.com/de", "https://x.com/de-at"]}].
    hreflang_conflicts: list[dict[str, Any]] = field(default_factory=list)
    # URLs claimed by more than one language code (x-default excluded), e.g.
    # [{"url": "https://x.com/en", "hreflang": ["en", "fr"]}].
    hreflang_duplicate_urls: list[dict[str, Any]] = field(default_factory=list)
    og_tags: dict[str, str] = field(default_factory=dict)
    twitter_tags: dict[str, str] = field(default_factory=dict)
    # Open Graph tags that are *declared but empty* (e.g. a CMS/plugin emitted
    # `<meta property="og:title" content="">`). These are a distinct defect from
    # a missing tag: the author intended to set a social title and produced a
    # broken one, so social platforms ignore the value and fall back
    # unpredictably. We surface them separately from `og_missing` so a present-
    # but-blank tag is not silently approved (the old check only tested key
    # presence, so an empty value slipped through as "fine").
    og_empty: list[str] = field(default_factory=list)
    # False = an Open Graph social card is partially configured (og:title and/or
    # og:description present with a real value) but og:image is absent; True =
    # the share thumbnail is missing. A share without a thumbnail is far less
    # likely to be clicked, yet og:image is the single most commonly forgotten
    # OG tag. None is never used: when no OG is declared at all we raise
    # og_missing instead, and when the title/description are merely empty we
    # raise og_empty instead, leaving this False in both cases.
    og_image_missing: bool = False
    has_robots_txt: bool | None = None
    has_sitemap: bool | None = None
    score: int = 0
    issues: list[Issue] = field(default_factory=list)
    # Severity breakdown of `issues`, pre-aggregated so a caller (agent / CI /
    # dashboard) can gauge the page's health at a glance without walking the
    # whole list — e.g. a CI gate "warnings > N → fail". Always present with all
    # three keys (zero-filled), even on a flawless page, and kept in sync with
    # `issues` by analyze_html (via `tally_issues`). Complements the
    # server-level `error_count` used by the CI-audit flow.
    issue_counts: dict[str, int] = field(
        default_factory=lambda: {"error": 0, "warning": 0, "info": 0}
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _rel_values(tag) -> list[str]:
    rel = tag.get("rel")
    if not rel:
        return []
    if isinstance(rel, str):
        return [r.lower() for r in rel.split()]
    return [r.lower() for r in rel]


# <link> rel values that make the browser actually FETCH a subresource.
# Everything else on <link> is metadata or a connection hint that is never
# loaded into the page: canonical, alternate/hreflang, prev/next, author, me,
# license, search, and the preconnect / dns-prefetch hints (which only warm up
# DNS/TCP and are explicitly not mixed content). An http:// href on those must
# never be reported as mixed content.
FETCHING_LINK_RELS: frozenset[str] = frozenset({
    "stylesheet",
    "icon",                            # also covers rel="shortcut icon"
    "apple-touch-icon",
    "apple-touch-icon-precomposed",
    "mask-icon",
    "fluid-icon",
    "preload",
    "modulepreload",
    "prefetch",
    "prerender",
    "manifest",
})


def _link_fetches_subresource(tag) -> bool:
    """True when a <link> tag causes the browser to load a subresource."""
    return bool(set(_rel_values(tag)) & FETCHING_LINK_RELS)


def _srcset_urls(value: str) -> list[str]:
    """Extract candidate URLs from a `srcset` attribute value.

    A srcset is a comma-separated list of ``"url [descriptor]"`` candidates; the
    descriptor (a pixel density like ``2x`` or a width like ``640w``) is
    optional and must not be mistaken for part of the URL. Only the first
    whitespace-separated token of each candidate is a URL.
    """
    urls: list[str] = []
    for candidate in value.split(","):
        token = candidate.strip().split()[0] if candidate.strip() else ""
        if token:
            urls.append(token)
    return urls


# Foreign-namespace elements whose <title> children are *not* the document
# title: SVG <title> is an accessible name for the graphic, MathML <title>
# likewise. Browsers and search engines only ever use the HTML <title>.
_FOREIGN_TITLE_PARENTS = frozenset({"svg", "math"})


def _page_title_tag(soup):
    """Return the document's real <title>, ignoring inline SVG/MathML titles.

    Inline icons carry their own accessible name (``<svg><title>Close
    menu</title></svg>``) and modern pages are full of them. Those elements
    live in the SVG namespace, so browsers and crawlers never treat them as
    the page title — but a namespace-unaware HTML parser happily returns the
    first ``<title>`` found anywhere in the tree. On a page whose real
    ``<title>`` is missing (very common in SPAs that set it from JavaScript)
    that meant reporting the menu icon's label as the page title and *hiding*
    a critical SEO defect behind a harmless "title is short" warning.
    """
    for tag in soup.find_all("title"):
        if any(parent.name in _FOREIGN_TITLE_PARENTS for parent in tag.parents):
            continue
        return tag
    return None


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
        report.issue_counts = tally_issues(report.issues)
        return report

    soup = BeautifulSoup(html, "html.parser")

    # --- <title> ---
    # Deliberately not `soup.title`: that would return an inline SVG icon's
    # <title> when the page has no real one (see _page_title_tag).
    title_tag = _page_title_tag(soup)
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

    # --- duplicate <title> elements ---
    # Only the *first* <title> in <head> is used by browsers, search engines and
    # social scrapers; any further <title> is silently dropped. Two titles almost
    # always mean a templating bug (a partial that re-includes the document
    # title), so the page's real title may not be the one the author intended —
    # a tight, high-signal authoring defect. Inline SVG/MathML <title> labels are
    # not document titles (handled by _page_title_tag) and must not count here.
    real_title_tags = [
        t for t in soup.find_all("title")
        if not any(parent.name in _FOREIGN_TITLE_PARENTS for parent in t.parents)
    ]
    if len(real_title_tags) > 1:
        report.issues.append(Issue(
            "warning", "title_duplicate",
            f"Found {len(real_title_tags)} <title> tags in the document; browsers "
            f"only use the first, so the extra title(s) are ignored."))

    # --- meta description ---
    meta_descs = soup.find_all("meta", attrs={"name": lambda v: v and v.lower() == "description"})
    report.meta_description_count = len(meta_descs)
    # Use the first non-empty declaration as the authoritative description.
    meta_desc = next(
        (m for m in meta_descs if m.get("content") and str(m["content"]).strip()),
        None,
    )
    if meta_desc is not None:
        report.meta_description = str(meta_desc["content"]).strip()
        report.meta_description_length = len(report.meta_description)
        if report.meta_description_length < 70:
            report.issues.append(Issue("warning", "desc_short", "Meta description is short (<70 chars)."))
        elif report.meta_description_length > 160:
            report.issues.append(Issue("warning", "desc_long",
                                        "Meta description exceeds 160 chars; may be truncated in SERP."))
    else:
        report.issues.append(Issue("warning", "desc_missing", "Missing meta description."))
    # Multiple description tags are a real-world trap: a CMS, a SEO plugin and a
    # hand-written tag each inject their own, and search engines use *one*
    # arbitrarily (often not the one you wrote), so your carefully tuned snippet
    # may never appear. This applies whether the duplicates are identical or
    # contradictory — the fix is always to keep a single authoritative tag.
    if report.meta_description_count > 1:
        report.issues.append(Issue(
            "warning", "desc_duplicate",
            f"Found {report.meta_description_count} <meta name=\"description\"> tags; "
            f"search engines use one arbitrarily, so keep a single authoritative "
            f"description."))

    # --- <html lang> ---
    html_tag = soup.find("html")
    if html_tag and html_tag.get("lang") and html_tag["lang"].strip():
        report.html_lang = html_tag["lang"].strip()
        # Declaring *a* lang is not enough: browsers, screen readers and
        # translation tools ignore a malformed tag entirely, so the page ends
        # up behaving as if no language were declared at all. Common real-world
        # mistakes: "english", "en_US" (underscore), "en-USA" (3-letter region).
        report.lang_valid = _is_valid_language_tag(report.html_lang)
        if not report.lang_valid:
            report.issues.append(Issue(
                "warning", "lang_invalid",
                f"Invalid <html lang> value '{report.html_lang}'; it is not a "
                f"valid BCP 47 language tag and will be ignored."))
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
    else:
        # Even with a viewport present, it can *lock* zoom for users — a real
        # WCAG 2.5.1 (Pointer Targets / Resize Text) failure that traps
        # low-vision users at 100%. Two ways it happens in the wild:
        #   - user-scalable=no (or =0)        -> explicit opt-out of zoom
        #   - maximum-scale=1 / 1.0 / 0.8 …   -> caps zoom at 100% (<=1.0)
        # We deliberately do NOT flag initial-scale, and we only flag a
        # maximum-scale that actually prevents zoom (<= 1.0), so a
        # `maximum-scale=2` (still allows 200% zoom) is correctly left alone —
        # keeps GlobeLens precise and free of false positives.
        vp_content = (vp.get("content") or "").lower()
        vp_pairs = {}
        for part in vp_content.split(","):
            if "=" in part:
                k, _, v = part.partition("=")
                vp_pairs[k.strip()] = v.strip()
        zoom_locked = False
        scale = vp_pairs.get("maximum-scale")
        if scale:
            try:
                if float(scale) <= 1.0:
                    zoom_locked = True
            except ValueError:
                pass  # non-numeric maximum-scale is malformed; don't guess
        if vp_pairs.get("user-scalable") in ("no", "0"):
            zoom_locked = True
        if zoom_locked:
            report.viewport_zoom_disabled = True
            report.issues.append(Issue(
                "warning", "viewport_zoom_disabled",
                "Viewport disables user zoom (user-scalable=no or "
                "maximum-scale<=1); low-vision users cannot enlarge the page "
                "(WCAG 2.5.1)."))

    # --- base href (affects how relative URLs resolve) ---
    # A page may declare <base href="...">; when it does, every *relative*
    # URL on the page (canonical, hreflang, …) is resolved against that base
    # rather than the document URL. The README promises that canonical /
    # hreflang are resolved to absolute URLs an agent can act on directly — so
    # we must honor <base> too, or we hand back wrong absolute URLs for any
    # page that uses one (common on CDN-fronted and templated deployments).
    # The first <base> wins (per the HTML spec); if it is relative itself we
    # resolve it against the document URL first. The page's own address, used
    # for the self-referencing hreflang check, never changes because of <base>.
    base_tag = soup.find("base", href=True)
    base_url = urljoin(url, base_tag["href"]) if base_tag else url

    # --- canonical / hreflang / og / twitter ---
    canonical_hrefs: list[str] = []
    for link in soup.find_all("link"):
        rels = _rel_values(link)
        if "canonical" in rels and link.get("href"):
            href = link.get("href").strip()
            canonical_hrefs.append(href)
        if "alternate" in rels and link.get("hreflang"):
            href = link.get("href")
            entry = {"hreflang": link.get("hreflang"), "href": href}
            if href:
                entry["abs_href"] = urljoin(base_url, href)
            report.hreflang.append(entry)

    # Multiple canonical links are a known trap: when two or more declare
    # *different* URLs, search engines ignore canonical signals for the page
    # entirely (the conflicting hints cancel out). We keep the first declaration
    # as the authoritative `canonical` and surface any disagreement so an agent
    # can reconcile them. Identifying duplicates pointing to the same URL (even
    # when written as relative vs absolute) is not a conflict.
    if canonical_hrefs:
        # Use the first non-empty declaration as the canonical link.
        report.canonical = canonical_hrefs[0]
        report.canonical_url = urljoin(base_url, canonical_hrefs[0])
        # De-duplicate on the resolved absolute URL to decide if they conflict.
        resolved = []
        for href in canonical_hrefs:
            abs_href = urljoin(base_url, href)
            if abs_href not in resolved:
                resolved.append(abs_href)
        report.canonical_urls = resolved
        if len(resolved) > 1:
            report.issues.append(Issue(
                "warning", "canonical_conflict",
                "Multiple canonical links point to different URLs "
                f"({', '.join(resolved)}); search engines ignore conflicting "
                f"canonical signals, so pick a single URL."))

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
        # hreflang cluster integrity: the alternate set is a map, and both
        # halves of it break in the wild.
        #   1. One code -> several URLs. A <link> block copied between locales
        #      keeps the previous language code, so e.g. "de" points at both
        #      /de and /de-at. Google treats the pair as contradictory and
        #      drops it, silently disabling the alternate.
        #   2. Several codes -> one URL. A missing translation gets
        #      "temporarily" pointed at the English page, so "fr" and "en"
        #      claim the same document; the wrong locale then wins in search
        #      results for one of them. x-default is exempt: it is *meant* to
        #      share a URL with the fallback language.
        # Comparison uses the same normalization as the self-reference check,
        # so "/en" vs "/en/" is a duplicate declaration, not a conflict.
        by_code: dict[str, list[str]] = {}
        by_url: dict[tuple[str, str, str, str], dict[str, Any]] = {}
        for h in report.hreflang:
            code = (h.get("hreflang") or "").strip().lower()
            target = h.get("abs_href") or h.get("href") or ""
            if not code or not target:
                continue
            url_key = _self_ref_key(target)
            targets = by_code.setdefault(code, [])
            if all(_self_ref_key(t) != url_key for t in targets):
                targets.append(target)
            if code != "x-default":
                slot = by_url.setdefault(url_key, {"url": target, "hreflang": []})
                if code not in slot["hreflang"]:
                    slot["hreflang"].append(code)

        report.hreflang_conflicts = [
            {"hreflang": code, "urls": targets}
            for code, targets in by_code.items()
            if len(targets) > 1
        ]
        if report.hreflang_conflicts:
            detail = "; ".join(
                f"{c['hreflang']} -> {', '.join(c['urls'])}"
                for c in report.hreflang_conflicts
            )
            report.issues.append(Issue(
                "warning", "hreflang_conflict",
                f"Conflicting hreflang declarations ({detail}); a language code "
                f"must resolve to a single URL or search engines discard the "
                f"contradictory alternates."))

        report.hreflang_duplicate_urls = [
            slot for slot in by_url.values() if len(slot["hreflang"]) > 1
        ]
        if report.hreflang_duplicate_urls:
            detail = "; ".join(
                f"{', '.join(s['hreflang'])} -> {s['url']}"
                for s in report.hreflang_duplicate_urls
            )
            report.issues.append(Issue(
                "warning", "hreflang_duplicate_url",
                f"One URL is claimed by several languages ({detail}); each "
                f"language version needs its own URL (only x-default may "
                f"share one)."))

        # Self-referencing hreflang: Google requires every page in an hreflang
        # cluster to also list *itself* as one of the alternates. When the
        # self-reference is missing, search engines may ignore the whole set —
        # a silent failure that is very common on hand-maintained i18n sites.
        # Compare on normalized URLs (case-insensitive host, trailing slash
        # insensitive) using each entry's resolved absolute href.
        page_key = _self_ref_key(url)
        self_entries = [
            h for h in report.hreflang
            if _self_ref_key(h.get("abs_href") or h.get("href") or "") == page_key
        ]
        report.hreflang_self_ref = bool(self_entries)
        if not report.hreflang_self_ref:
            report.issues.append(Issue(
                "warning", "hreflang_no_self_ref",
                "hreflang set does not reference this page itself; Google "
                "requires a self-referencing hreflang link, otherwise the "
                "whole cluster may be ignored."))
        else:
            # Cross-signal consistency: the page's own hreflang entry says
            # "this page is language X" to search engines, while <html lang>
            # says "this page is language Y" to browsers, screen readers and
            # translation tools. When X != Y one of them is wrong — a very
            # common copy-paste bug on templated i18n sites that degrades
            # both accessibility and international search results.
            # Only the primary subtag is compared, so "en" vs "en-GB" (a
            # region-only difference) is deliberately not flagged.
            self_langs = {
                _primary_subtag(h.get("hreflang"))
                for h in self_entries
                if h.get("hreflang")
                and h["hreflang"].strip().lower() != "x-default"
                and _is_valid_hreflang(h.get("hreflang"))
            }
            if self_langs and report.html_lang and report.lang_valid:
                page_lang = _primary_subtag(report.html_lang)
                report.lang_hreflang_mismatch = page_lang not in self_langs
                if report.lang_hreflang_mismatch:
                    report.issues.append(Issue(
                        "warning", "lang_hreflang_mismatch",
                        f"<html lang=\"{report.html_lang}\"> disagrees with this "
                        f"page's own hreflang value(s) "
                        f"({', '.join(sorted(self_langs))}); browsers and search "
                        f"engines will infer different languages for this page."))

    # --- Open Graph presence (and the empty-value false negative) ---
    # A social preview needs both og:title and og:description. A *missing* tag is
    # an info-level gap; a tag that is *declared but empty* (`content=""`) is a
    # distinct, more specific defect — the author tried to set a title and
    # produced a broken one. The old check only tested key presence
    # (`"og:title" in og_tags`), so an empty value slipped through as "fine".
    # We now treat empty content as absent for the presence check, and separately
    # flag genuinely empty tags so a broken social card is never approved.
    og_title_raw = report.og_tags.get("og:title")
    og_desc_raw = report.og_tags.get("og:description")
    og_title_ok = bool(og_title_raw and og_title_raw.strip())
    og_desc_ok = bool(og_desc_raw and og_desc_raw.strip())
    if not og_title_ok or not og_desc_ok:
        empty_keys = [
            key for key, ok in (("og:title", og_title_ok), ("og:description", og_desc_ok))
            if not ok and key in report.og_tags
        ]
        if empty_keys:
            # declared-but-empty: a real broken tag, not a mere omission
            report.og_empty = empty_keys
            report.issues.append(Issue(
                "warning", "og_empty",
                f"Open Graph tag(s) declared but empty ({', '.join(empty_keys)}); "
                f"social platforms ignore the empty value and your share preview "
                f"falls back unpredictably."))
        else:
            report.issues.append(Issue("info", "og_missing", "Missing Open Graph tags; weak social sharing preview."))

    # --- Open Graph image presence (social thumbnail) ---
    # og:image is the most impactful OG tag for click-through: a share without a
    # thumbnail is text-only and gets far fewer clicks. Yet it is the single
    # most commonly forgotten one — teams set og:title + og:description and ship
    # without the image. We only flag it when a social card is *partially*
    # configured (at least one of og:title / og:description carries a real value)
    # but og:image is absent, so a page with no OG at all keeps firing og_missing
    # (not this), and a page whose title/description are merely empty keeps
    # firing og_empty (not this). That keeps the signal tight and avoids nagging
    # twice about a half-broken card.
    if (og_title_ok or og_desc_ok) and "og:image" not in report.og_tags:
        report.og_image_missing = True
        report.issues.append(Issue(
            "info", "og_image_missing",
            "Open Graph tags present (og:title / og:description) but og:image "
            "is missing; shared links will show no thumbnail, hurting click-through."))

    # --- favicon / browser-tab icon presence ---
    # A missing favicon weakens brand recognition in browser tabs, bookmarks and
    # search-result snippets that display one, and is a cheap, single-line fix
    # many sites genuinely forget. We accept any of the conventional icon rel
    # values as "present" (icon / shortcut icon / apple-touch-icon / mask-icon /
    # fluid-icon) — the exact form is a stylistic choice, not an audit failure.
    # This is a link-declaration check only: GlobeLens does not fetch
    # /favicon.ico, consistent with the analyzer's network-free design.
    _FAVICON_RELS = {"icon", "shortcut icon", "apple-touch-icon",
                     "apple-touch-icon-precomposed", "mask-icon", "fluid-icon"}
    has_favicon = False
    for link in soup.find_all("link"):
        if _FAVICON_RELS & set(_rel_values(link)):
            has_favicon = True
            break
    report.has_favicon = has_favicon
    if not has_favicon:
        report.issues.append(Issue(
            "info", "favicon_missing",
            "No favicon <link> found; add one so the page shows a brand icon "
            "in tabs, bookmarks and search results."))

    # --- crawl / index control: meta robots ---
    meta_robots = soup.find("meta", attrs={"name": lambda v: v and v.lower() == "robots"})
    if meta_robots and meta_robots.get("content") and meta_robots["content"].strip():
        report.meta_robots = meta_robots["content"].strip()
        directives = [d.strip().lower() for d in report.meta_robots.split(",")]
        if "noindex" in directives:
            report.issues.append(Issue("warning", "robots_noindex",
                                       "Page is marked noindex; search engines will exclude it from results."))

    # --- client-side redirect / auto-reload: <meta http-equiv="refresh"> ---
    # With a `url=` target this is a client-side substitute for a real HTTP 3xx.
    # Google's guidance is to use a server-side 301 instead: a meta refresh only
    # fires after the page has loaded (slower, and a visible flash for the
    # user), and it is a weaker signal for consolidating ranking onto the
    # destination. It is also the classic way i18n sites auto-forward visitors
    # by language, which traps crawlers on the redirecting page.
    # Without a target the page simply reloads itself on a timer, which fails
    # WCAG 2.2.1 (Timing Adjustable) — the user cannot pause, stop or extend it,
    # and any work in progress on the page is discarded.
    meta_refresh = soup.find(
        "meta", attrs={"http-equiv": lambda v: v and v.lower() == "refresh"}
    )
    refresh_content = (meta_refresh.get("content") or "") if meta_refresh else ""
    if refresh_content.strip():
        m = _META_REFRESH_RE.match(refresh_content)
        if m:
            report.meta_refresh = refresh_content.strip()
            report.meta_refresh_delay = int(m.group("delay") or 0)
            # The target may be wrapped in single or double quotes.
            target = (m.group("url") or "").strip().strip("'\"").strip()
            if target:
                report.meta_refresh_url = urljoin(url, target)
                report.issues.append(Issue(
                    "warning", "meta_refresh_redirect",
                    f"Client-side redirect to {report.meta_refresh_url} via "
                    f"<meta http-equiv=\"refresh\"> after "
                    f"{report.meta_refresh_delay}s; use a server-side 301/302 "
                    f"so search engines pass ranking signals to the target."))
            else:
                report.issues.append(Issue(
                    "info", "meta_refresh_reload",
                    f"Page reloads itself every {report.meta_refresh_delay}s via "
                    f"<meta http-equiv=\"refresh\">; users cannot pause or "
                    f"extend it (WCAG 2.2.1 Timing Adjustable)."))

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

    # --- on-page media: image alt text + layout stability ---
    imgs = soup.find_all("img")
    report.images_total = len(imgs)
    report.images_missing_alt = sum(
        1 for img in imgs if not (img.get("alt") and str(img.get("alt")).strip())
    )
    report.images_missing_dims = sum(
        1 for img in imgs if not img.get("width") and not img.get("height")
    )
    if report.images_total > 0 and report.images_missing_alt > 0:
        report.issues.append(Issue(
            "warning", "images_missing_alt",
            f"{report.images_missing_alt} of {report.images_total} <img> tags missing alt text "
            f"(hurts accessibility and image SEO)."))
    if report.images_total > 0 and report.images_missing_dims > 0:
        report.issues.append(Issue(
            "info", "images_missing_dims",
            f"{report.images_missing_dims} of {report.images_total} <img> tags have no explicit "
            f"width/height; without them the browser cannot reserve space, causing layout shift "
            f"(CLS) as images load."))

    # --- insecure subresources: mixed content on HTTPS pages ---
    # Browsers block/flag plaintext HTTP resources loaded from an HTTPS page;
    # these silently break rendering and erode user trust / SEO. Only flag when
    # the page itself is served over HTTPS (relative and protocol-relative URLs
    # such as "/x.png" or "//x.png" inherit HTTPS and are NOT mixed content).
    # For <link> we only consider rel values that actually fetch a subresource
    # (stylesheet, icon, preload, manifest, …) — an http:// canonical, hreflang
    # alternate or preconnect hint is never loaded by the browser and reporting
    # it here would be a false positive.
    if urlparse(url).scheme == "https":
        for tag in soup.find_all(
            ["img", "script", "link", "iframe", "source", "audio", "video", "embed"]
        ):
            if tag.name == "link" and not _link_fetches_subresource(tag):
                continue
            attr = "href" if tag.name == "link" else "src"
            val = tag.get(attr)
            if isinstance(val, str):
                val = val.strip()
                if val.lower().startswith("http://"):
                    report.mixed_content.append(
                        {"tag": tag.name, "attr": attr, "url": val}
                    )
            # `srcset` (responsive images on <img> / <source>) is a separate
            # attribute the browser still loads — an http:// entry there is just
            # as much mixed content as one in `src`, but the check above only
            # looked at `src`, so image-heavy / responsive sites were silently
            # missing it (browsers block it the same way). The https candidate
            # in a srcset is, correctly, NOT mixed content.
            if tag.name in ("img", "source"):
                ss = tag.get("srcset")
                if isinstance(ss, str):
                    for u in _srcset_urls(ss):
                        if u.lower().startswith("http://"):
                            report.mixed_content.append(
                                {"tag": tag.name, "attr": "srcset", "url": u}
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
    # Only `<a name="...">` is a legacy fragment target ("find a potential
    # indicated element" in the HTML spec: an id match, or an *a* element with
    # a matching name). The `name` attribute means something entirely
    # different on other elements — form control names (`<input name="q">`),
    # metadata keys (`<meta name="description">`), browsing-context names
    # (`<iframe name="preview">`) — and none of them can be jumped to.
    # Accepting them made GlobeLens silently approve genuinely broken links
    # such as href="#description" on any page with a meta description.
    for el in soup.find_all("a", attrs={"name": True}):
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
        # Browsers percent-decode the fragment before matching it against
        # element ids (URL spec), and static-site generators routinely write
        # non-ASCII heading anchors percent-encoded in the href while the id
        # stays as literal text (e.g. href="#%E4%B8%AD%E6%96%87" targeting
        # id="中文"). Compare the decoded form too, so CJK / accented anchors
        # on i18n sites are not falsely reported as broken.
        decoded = unquote(frag)
        if frag in anchor_targets or decoded in anchor_targets:
            continue
        if decoded in seen_anchor:
            continue
        seen_anchor.add(decoded)
        report.broken_anchors.append({
            "href": href,
            "text": (a.get_text() or "").strip()[:80],
        })
    if report.broken_anchors:
        report.issues.append(Issue(
            "warning", "broken_anchors",
            f"Found {len(report.broken_anchors)} in-page anchor link(s) pointing to a "
            f"missing #fragment target; they do nothing when clicked."))

    # --- insecure cross-origin new-tab links (reverse tabnabbing) ---
    # An <a target="_blank"> whose rel lacks "noopener"/"noreferrer" lets the
    # page it opens reach back into window.opener and redirect the original tab
    # (a classic "reverse tabnabbing" phishing vector), and it costs the opener
    # a process. This is the well-known Lighthouse "unsafe links" audit. Only a
    # *cross-origin* web navigation (http/https to a different host) carries the
    # risk: same-origin links and non-http(s) hrefs (mailto:, tel:, javascript:,
    # in-page #anchors) cannot leak an opener, so we scope to cross-origin http(s)
    # links to avoid false positives. A link that is already protected by
    # rel="noopener" or rel="noreferrer" is skipped.
    page_parsed = urlparse(url)
    page_origin = (
        f"{page_parsed.scheme.lower()}://{page_parsed.netloc.lower()}"
        if page_parsed.scheme in ("http", "https") and page_parsed.netloc
        else None
    )
    for a in soup.find_all("a"):
        if (a.get("target") or "").strip().lower() != "_blank":
            continue
        href = a.get("href")
        if not isinstance(href, str) or not href.strip():
            continue
        href = href.strip()
        link_parsed = urlparse(urljoin(base_url, href))
        if link_parsed.scheme not in ("http", "https"):
            continue  # not a web navigation (mailto:, javascript:, #anchor…)
        if page_origin is None:
            continue  # cannot decide same vs cross origin; skip to stay safe
        link_origin = f"{link_parsed.scheme.lower()}://{link_parsed.netloc.lower()}"
        if link_origin == page_origin:
            continue  # same origin: no opener-leak risk
        if "noopener" in _rel_values(a) or "noreferrer" in _rel_values(a):
            continue  # already protected
        report.unsafe_blank_links.append({
            "href": href,
            "text": (a.get_text() or "").strip()[:80],
        })
    if report.unsafe_blank_links:
        report.issues.append(Issue(
            "warning", "unsafe_blank_link",
            f"Found {len(report.unsafe_blank_links)} external target=\"_blank\" "
            f"link(s) without rel=\"noopener noreferrer\"; they expose "
            f"window.opener (reverse tabnabbing) and waste resources."))

    # --- content depth: thin-content / body word count ---
    # Search engines treat pages with very little original text as low-value
    # ("thin content"). We count *visible* body words, deliberately excluding
    # <script>/<style> boilerplate, so an agent can spot pages that need more
    # substance. Pure HTML, network-free, and non-mutating (we don't decompose
    # tags, so later checks are unaffected). Counting is script-aware: Chinese,
    # Japanese and Thai text has no spaces, so a naive whitespace split would
    # score a full-length article as ~1 word and flag it as thin.
    body = soup.body or soup
    visible_text = " ".join(
        s
        for s in body.find_all(string=True)
        if s.parent is not None and s.parent.name not in ("script", "style")
    )
    report.word_count = _count_words(visible_text)
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
    report.issue_counts = tally_issues(report.issues)
    return report


def robots_sitemap_urls(url: str) -> tuple[str, str]:
    """Derive the canonical robots.txt and sitemap.xml URLs for a page URL."""
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    return urljoin(base, "/robots.txt"), urljoin(base, "/sitemap.xml")
