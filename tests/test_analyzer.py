from globe_lens_mcp.analyzer import analyze_html, THIN_CONTENT_MIN_WORDS

SAMPLE_GOOD = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Example Global Site — Going Global Made Simple</title>
  <meta name="description" content="A sample site used to test GlobeLens SEO and internationalization analysis logic end to end, with proper meta tags.">
  <link rel="canonical" href="https://example.com/">
  <link rel="alternate" hreflang="en" href="https://example.com/en">
  <link rel="alternate" hreflang="x-default" href="https://example.com/">
  <meta property="og:title" content="Example">
  <meta property="og:description" content="desc">
  <script type="application/ld+json">{"@context":"https://schema.org","@type":"WebSite","name":"Example"}</script>
</head>
<body><h1>Hi</h1></body>
</html>"""

SAMPLE_BAD = "<html><head><title>x</title></head><body></body></html>"


def test_detects_good_signals():
    r = analyze_html(SAMPLE_GOOD, "https://example.com")
    assert r.html_lang == "en"
    assert r.title == "Example Global Site — Going Global Made Simple"
    assert r.charset == "utf-8"
    assert r.viewport is True
    assert r.canonical == "https://example.com/"
    assert len(r.hreflang) == 2
    assert any(h["hreflang"] == "x-default" for h in r.hreflang)
    assert "og:title" in r.og_tags
    assert r.score >= 90


def test_flags_missing_lang():
    r = analyze_html(SAMPLE_BAD, "https://example.com")
    codes = [i.code for i in r.issues]
    assert "lang_missing" in codes
    assert r.html_lang is None


SAMPLE_STRUCTURE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Structure Demo</title>
</head>
<body>
  <h1>First heading</h1>
  <h1>Second heading</h1>
  <img src="/a.png">
  <img src="/b.png" alt="">
  <img src="/c.png" alt="ok">
</body>
</html>"""


def test_flags_onpage_structure_issues():
    r = analyze_html(SAMPLE_STRUCTURE, "https://example.com")
    codes = [i.code for i in r.issues]
    assert "h1_multiple" in codes
    assert r.h1_count == 2
    assert r.images_total == 3
    assert r.images_missing_alt == 2
    assert "images_missing_alt" in codes


SAMPLE_SINGLE_H1_NO_IMG = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Single H1</title></head>
<body><h1>Main heading</h1><p>Just text</p></body></html>"""


def test_clean_onpage_structure_has_no_structure_issues():
    r = analyze_html(SAMPLE_SINGLE_H1_NO_IMG, "https://example.com")
    codes = [i.code for i in r.issues]
    assert "h1_missing" not in codes
    assert "h1_multiple" not in codes
    assert "images_missing_alt" not in codes
    assert r.h1_count == 1
    assert r.images_total == 0
    assert r.images_missing_alt == 0


SAMPLE_CRAWL = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Crawl Control Demo</title>
<meta name="robots" content="noindex, nofollow">
</head><body><h1>Hi</h1></body></html>"""

SAMPLE_STRUCTURED = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Structured Data Demo</title>
<script type="application/ld+json">{"@context":"https://schema.org","@type":"Article"}</script>
</head><body><h1>Hi</h1></body></html>"""


def test_flags_noindex_from_meta_robots():
    r = analyze_html(SAMPLE_CRAWL, "https://example.com")
    codes = [i.code for i in r.issues]
    assert "robots_noindex" in codes
    assert r.meta_robots == "noindex, nofollow"
    assert r.has_json_ld is False
    assert "json_ld_missing" in codes


def test_detects_json_ld_and_skips_missing_warning():
    r = analyze_html(SAMPLE_STRUCTURED, "https://example.com")
    codes = [i.code for i in r.issues]
    assert r.has_json_ld is True
    assert "json_ld_missing" not in codes
    # a normal indexable page carries no noindex warning
    assert "robots_noindex" not in codes


SAMPLE_RELATIVE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Relative Links Demo</title>
<link rel="canonical" href="/products/widget">
<link rel="alternate" hreflang="en" href="/en">
<link rel="alternate" hreflang="x-default" href="/">
</head><body><h1>Hi</h1></body></html>"""


def test_resolves_relative_canonical_and_hreflang():
    page_url = "https://example.com/some/deep/page"
    r = analyze_html(SAMPLE_RELATIVE, page_url)
    # canonical is kept verbatim but also resolved to an absolute URL
    assert r.canonical == "/products/widget"
    assert r.canonical_url == "https://example.com/products/widget"
    # every hreflang entry gets an absolute abs_href resolved against the page
    assert len(r.hreflang) == 2
    hrefs = {h["hreflang"]: h.get("abs_href") for h in r.hreflang}
    assert hrefs["en"] == "https://example.com/en"
    assert hrefs["x-default"] == "https://example.com/"


def test_handles_empty_html_safely():
    r = analyze_html("", "https://example.com")
    codes = [i.code for i in r.issues]
    assert "empty_html" in codes
    assert r.score == 0
    # raw input (None) should also be safe, not crash
    r2 = analyze_html(None, "https://example.com")  # type: ignore[arg-type]
    assert any(i.code == "empty_html" for i in r2.issues)
    assert r2.score == 0


SAMPLE_MIXED = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Mixed Content Demo</title>
<link rel="stylesheet" href="http://cdn.example.com/style.css">
</head><body>
<h1>Hi</h1>
<img src="http://cdn.example.com/a.png" alt="ok">
<script src="http://cdn.example.com/app.js"></script>
</body></html>"""


def test_flags_mixed_content_on_https_page():
    r = analyze_html(SAMPLE_MIXED, "https://example.com")
    codes = [i.code for i in r.issues]
    assert "mixed_content" in codes
    # three insecure http:// subresources: link + img + script
    assert len(r.mixed_content) == 3
    tags = {m["tag"] for m in r.mixed_content}
    assert {"link", "img", "script"} <= tags
    # each entry records where to fix
    assert all(m["attr"] in ("href", "src") for m in r.mixed_content)


def test_no_mixed_content_for_relative_or_http_page():
    # relative + https resources on an https page are NOT mixed content
    https_ok = analyze_html(
        '<html lang="en"><head><meta charset="utf-8"><title>ok</title>'
        '<link rel="stylesheet" href="/style.css"></head>'
        '<body><h1>Hi</h1><img src="https://cdn.example.com/a.png" alt="ok"></body></html>',
        "https://example.com",
    )
    assert https_ok.mixed_content == []
    assert "mixed_content" not in [i.code for i in https_ok.issues]

    # an http:// page loading http:// resources is not "mixed" (no upgrade needed)
    http_page = analyze_html(SAMPLE_MIXED, "http://example.com")
    assert http_page.mixed_content == []
    assert "mixed_content" not in [i.code for i in http_page.issues]


SAMPLE_ANCHORS = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Anchor Demo</title></head><body>
<h1>Hi</h1>
<a id="top"></a>
<nav>
  <a href="#top">Back to top</a>
  <a href="#features">Features</a>
  <a href="#pricing">Pricing</a>
  <a href="#">Empty link</a>
</nav>
<section id="features"><h2>Features</h2></section>
</body></html>"""


def test_flags_broken_inpage_anchors():
    r = analyze_html(SAMPLE_ANCHORS, "https://example.com")
    codes = [i.code for i in r.issues]
    # "#features" resolves (id present), "#top" resolves (id present),
    # "#pricing" is dangling, and href="#" is a valid scroll-to-top (ignored).
    assert "broken_anchors" in codes
    assert len(r.broken_anchors) == 1
    broken = r.broken_anchors[0]
    assert broken["href"] == "#pricing"
    assert "text" in broken  # the visible link text is captured for easy fixing


def test_ignores_valid_anchors_and_top_link():
    good = analyze_html(
        '<html lang="en"><head><meta charset="utf-8"><title>ok</title></head>'
        '<body><h1>Hi</h1>'
        '<a id="contact"></a>'
        '<a href="#contact">Contact</a>'
        '<a href="#">Top</a>'
        '</body></html>',
        "https://example.com",
    )
    assert good.broken_anchors == []
    assert "broken_anchors" not in [i.code for i in good.issues]


def test_flags_page_truncated():
    r = analyze_html(SAMPLE_GOOD, "https://example.com", truncated=True)
    codes = [i.code for i in r.issues]
    assert "page_truncated" in codes


_SENTENCE = "GlobeLens audits websites for seo and internationalization readiness."

SAMPLE_THIN = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Thin Content Demo</title></head>
<body><h1>Hi</h1><p>Short.</p>
<script>var x = "this boilerplate must not count as body content";</script>
</body></html>"""

# 8 words per sentence * 40 = 320 visible words, safely above the 300 threshold.
SAMPLE_RICH = (
    "<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">\n"
    "<title>Rich Content Demo</title></head>\n<body><h1>Welcome</h1><p>"
    + " ".join([_SENTENCE] * 40)
    + "</p></body></html>"
)


def test_flags_thin_content_excluding_script_text():
    r = analyze_html(SAMPLE_THIN, "https://example.com")
    codes = [i.code for i in r.issues]
    # a two-word body is flagged as thin, and script/style text is NOT counted
    assert "thin_content" in codes
    assert r.word_count == 2


def test_skips_thin_content_for_rich_page():
    r = analyze_html(SAMPLE_RICH, "https://example.com")
    codes = [i.code for i in r.issues]
    assert "thin_content" not in codes
    # 40 repetitions * 8 words + the "Welcome" <h1> = 321 visible words, above
    # the 300 threshold
    assert r.word_count > THIN_CONTENT_MIN_WORDS
    assert r.word_count == 40 * 8 + 1


# A page that triggers all three severity tiers at once: a missing <html lang>
# (error), a missing viewport (warning), and no hreflang / OG / JSON-LD (info).
SAMPLE_PRIORITIZED = """<!doctype html>
<html><head><meta charset="utf-8">
<title>Hi</title></head><body><h1>Hi</h1></body></html>"""


def test_issues_sorted_by_severity_most_severe_first():
    r = analyze_html(SAMPLE_PRIORITIZED, "https://example.com")
    priorities = [i.priority for i in r.issues]
    # highest-priority (largest) issues come first, strictly descending
    assert priorities == sorted(priorities, reverse=True)
    assert r.issues[0].severity == "error"
    assert r.issues[-1].severity == "info"


def test_issue_priority_matches_severity_rank():
    from globe_lens_mcp.analyzer import SEVERITY_RANK

    r = analyze_html(SAMPLE_PRIORITIZED, "https://example.com")
    for issue in r.issues:
        assert issue.priority == SEVERITY_RANK[issue.severity]


# --- Coverage for social cards (OG / Twitter) and the URL-derivation helper ---
# These behaviors were implemented in earlier days but had only implicit /
# incidental coverage. Locking them down directly so a refactor cannot silently
# drop a captured tag or break robots/sitemap URL derivation.
SAMPLE_SOCIAL = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Social Demo</title>
<meta property="og:title" content="Example">
<meta property="og:description" content="desc">
<meta property="og:image" content="https://example.com/og.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Example TW">
<meta name="twitter:description" content="desc TW">
</head><body><h1>Hi</h1></body></html>"""


def test_captures_og_and_twitter_card_tags():
    r = analyze_html(SAMPLE_SOCIAL, "https://example.com")
    # full Open Graph chain is captured
    assert r.og_tags.get("og:title") == "Example"
    assert r.og_tags.get("og:description") == "desc"
    assert r.og_tags.get("og:image") == "https://example.com/og.png"
    # Twitter card tags are captured under their own namespace
    assert r.twitter_tags.get("twitter:card") == "summary_large_image"
    assert r.twitter_tags.get("twitter:title") == "Example TW"
    assert r.twitter_tags.get("twitter:description") == "desc TW"
    # both og:title and og:description present -> the og_missing info is NOT fired
    assert "og_missing" not in [i.code for i in r.issues]


def test_flags_missing_og_tags():
    # SAMPLE_BAD has no OG tags at all -> the og_missing info must fire
    r = analyze_html(SAMPLE_BAD, "https://example.com")
    assert "og_missing" in [i.code for i in r.issues]


def test_robots_sitemap_urls_across_url_shapes():
    from globe_lens_mcp.analyzer import robots_sitemap_urls

    # bare origin -> robots/sitemap at root
    assert robots_sitemap_urls("https://example.com") == (
        "https://example.com/robots.txt", "https://example.com/sitemap.xml")
    # deep path -> the base is still the origin (not the path)
    assert robots_sitemap_urls("https://example.com/products/widget") == (
        "https://example.com/robots.txt", "https://example.com/sitemap.xml")
    # non-https scheme is preserved
    assert robots_sitemap_urls("http://example.com/a") == (
        "http://example.com/robots.txt", "http://example.com/sitemap.xml")
    # query string / fragment are stripped from the derived base
    assert robots_sitemap_urls("https://example.com/p?x=1#frag") == (
        "https://example.com/robots.txt", "https://example.com/sitemap.xml")
    # non-standard port stays on the origin
    assert robots_sitemap_urls("https://sub.example.com:8080/x") == (
        "https://sub.example.com:8080/robots.txt",
        "https://sub.example.com:8080/sitemap.xml")


SAMPLE_NO_CHARSET = """<!doctype html>
<html lang="en"><head><title>No Charset Demo</title></head>
<body><h1>Hi</h1></body></html>"""


def test_flags_missing_charset():
    r = analyze_html(SAMPLE_NO_CHARSET, "https://example.com")
    assert r.charset is None
    assert "charset_missing" in [i.code for i in r.issues]


# --- hreflang value validity (i18n) ---
# Malformed hreflang codes are one of the most common real i18n mistakes and
# are silently ignored by search engines, so the intended alternate is lost.
SAMPLE_HREFLANG_INVALID = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Hreflang Validity Demo</title>
<link rel="alternate" hreflang="en-US" href="https://example.com/en-us">
<link rel="alternate" hreflang="en_GB" href="https://example.com/en-gb">
<link rel="alternate" hreflang="english" href="https://example.com/en">
<link rel="alternate" hreflang="x-default" href="https://example.com/">
</head><body><h1>Hi</h1></body></html>"""


def test_flags_invalid_hreflang_codes():
    r = analyze_html(SAMPLE_HREFLANG_INVALID, "https://example.com")
    codes = [i.code for i in r.issues]
    assert "hreflang_invalid" in codes
    # "en_GB" (underscore) and "english" (full word) are invalid; "en-US" and
    # "x-default" are valid and must NOT be flagged.
    assert set(r.invalid_hreflang) == {"en_GB", "english"}


def test_accepts_well_formed_hreflang_codes():
    # SAMPLE_GOOD uses "en" and "x-default", both valid -> no invalid list, no issue
    r = analyze_html(SAMPLE_GOOD, "https://example.com")
    assert r.invalid_hreflang == []
    assert "hreflang_invalid" not in [i.code for i in r.issues]


# --- charset via legacy http-equiv Content-Type ---
# Besides the HTML5 "<meta charset>" form, a huge number of real (older /
# non-English) pages declare their encoding with the legacy
# "<meta http-equiv='Content-Type' content='text/html; charset=...'>" form.
# Only accepting the HTML5 form produced a false "charset_missing" warning, so
# both are now honoured.
SAMPLE_HTTP_EQUIV_CHARSET = """<!doctype html>
<html lang="zh-CN"><head>
<meta http-equiv="Content-Type" content="text/html; charset=gb2312">
<title>Legacy Charset Demo Page Title Here</title>
</head><body><h1>Hi</h1></body></html>"""


def test_reads_charset_from_http_equiv_content_type():
    r = analyze_html(SAMPLE_HTTP_EQUIV_CHARSET, "https://example.com")
    # the legacy declaration is honoured and the value is extracted...
    assert r.charset == "gb2312"
    # ...so the false "charset_missing" warning is NOT emitted
    assert "charset_missing" not in [i.code for i in r.issues]


def test_html5_charset_still_wins_and_is_read():
    # the modern form keeps working unchanged
    html = (
        '<html lang="en"><head><meta charset="UTF-8">'
        "<title>Modern Charset Demo Title Long Enough</title></head>"
        "<body><h1>Hi</h1></body></html>"
    )
    r = analyze_html(html, "https://example.com")
    assert r.charset == "UTF-8"
    assert "charset_missing" not in [i.code for i in r.issues]


def test_still_flags_charset_missing_when_neither_form_present():
    # a page with no charset declaration at all is still flagged
    html = (
        '<html lang="en"><head>'
        "<title>No Charset At All Demo Title Here</title></head>"
        "<body><h1>Hi</h1></body></html>"
    )
    r = analyze_html(html, "https://example.com")
    assert r.charset is None
    assert "charset_missing" in [i.code for i in r.issues]


# --- self-referencing hreflang (i18n) ---
# Google requires every page in an hreflang cluster to also list *itself* as an
# alternate. A missing self-reference can make search engines ignore the whole
# set — a silent, very common failure on hand-maintained i18n sites.
SAMPLE_NO_SELF_REF = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Self Reference Demo Page Title Here</title>
<link rel="alternate" hreflang="de" href="https://example.com/de">
<link rel="alternate" hreflang="fr" href="https://example.com/fr">
</head><body><h1>Hi</h1></body></html>"""


def test_flags_missing_hreflang_self_reference():
    # page is /en but the hreflang set only lists /de and /fr -> flagged
    r = analyze_html(SAMPLE_NO_SELF_REF, "https://example.com/en")
    assert r.hreflang_self_ref is False
    assert "hreflang_no_self_ref" in [i.code for i in r.issues]


def test_accepts_self_referencing_hreflang_with_normalization():
    # SAMPLE_GOOD is audited at "https://example.com" (no trailing slash) and
    # its x-default alternate points to "https://example.com/" (with slash) —
    # normalization must treat these as the same page, so no false positive.
    r = analyze_html(SAMPLE_GOOD, "https://example.com")
    assert r.hreflang_self_ref is True
    assert "hreflang_no_self_ref" not in [i.code for i in r.issues]


def test_self_ref_resolves_relative_hreflang_and_host_case():
    # a *relative* self-referencing alternate and a differently-cased host must
    # both be recognized (compare on resolved, normalized URLs)
    html = (
        '<html lang="en"><head><meta charset="utf-8">'
        "<title>Relative Self Reference Demo Title</title>"
        '<link rel="alternate" hreflang="en" href="/en">'
        '<link rel="alternate" hreflang="de" href="/de">'
        "</head><body><h1>Hi</h1></body></html>"
    )
    r = analyze_html(html, "https://EXAMPLE.com/en")
    assert r.hreflang_self_ref is True
    assert "hreflang_no_self_ref" not in [i.code for i in r.issues]


def test_self_ref_not_applicable_without_hreflang():
    # pages with no hreflang at all: the check is N/A (None), never flagged
    r = analyze_html(SAMPLE_BAD, "https://example.com")
    assert r.hreflang_self_ref is None
    assert "hreflang_no_self_ref" not in [i.code for i in r.issues]




def test_every_emitted_issue_carries_actionable_fix_hint():
    # every issue produced by the analyzer must ship with a concrete remedy,
    # and the hint must survive serialization (what MCP clients actually see)
    r = analyze_html(SAMPLE_BAD, "https://example.com")
    assert r.issues, "expected SAMPLE_BAD to produce issues"
    for issue in r.issues:
        assert issue.fix, f"issue {issue.code} has no fix hint"
        assert issue.fix != issue.message  # remedy, not a restated problem
    serialized = r.to_dict()
    assert all(i["fix"] for i in serialized["issues"])
    # degenerate input path must carry a fix hint too
    r_empty = analyze_html("", "https://example.com")
    assert r_empty.issues[0].code == "empty_html"
    assert r_empty.issues[0].fix


def test_fix_hints_cover_every_issue_code_in_analyzer():
    # lock the FIX_HINTS table to the analyzer source: adding a new Issue(...)
    # without a matching fix hint must fail this test, so the two never drift
    import inspect
    import re as _re

    from globe_lens_mcp import analyzer

    source = inspect.getsource(analyzer)
    emitted_codes = set(_re.findall(r'Issue\(\s*"[a-z]+",\s*"([a-z0-9_]+)"', source))
    assert emitted_codes, "expected to find Issue(...) codes in analyzer source"
    missing = emitted_codes - set(analyzer.FIX_HINTS)
    assert not missing, f"issue codes without a fix hint: {sorted(missing)}"


def test_explicit_fix_overrides_lookup_and_unknown_code_is_empty():
    from globe_lens_mcp.analyzer import Issue

    custom = Issue("warning", "title_short", "msg", fix="Custom remedy.")
    assert custom.fix == "Custom remedy."  # explicit fix wins over the table
    unknown = Issue("info", "not_a_real_code", "msg")
    assert unknown.fix == ""  # unknown codes degrade gracefully
