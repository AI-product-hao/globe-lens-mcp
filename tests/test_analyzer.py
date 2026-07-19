from globe_lens_mcp.analyzer import analyze_html

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


