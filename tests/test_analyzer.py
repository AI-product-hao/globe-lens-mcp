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


SAMPLE_CANON_CONFLICT = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Canonical Conflict Demo</title>
<link rel="canonical" href="https://example.com/">
<link rel="canonical" href="https://example.com/home">
</head><body><h1>Hi</h1></body></html>"""

SAMPLE_CANON_DUP = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Canonical Duplicate Demo</title>
<link rel="canonical" href="/">
<link rel="canonical" href="https://example.com/">
</head><body><h1>Hi</h1></body></html>"""


def test_flags_conflicting_canonical_links():
    # Two <link rel="canonical"> pointing at different URLs: Google ignores the
    # whole canonical signal, so this must be surfaced (and not crash).
    r = analyze_html(SAMPLE_CANON_CONFLICT, "https://example.com")
    codes = [i.code for i in r.issues]
    assert "canonical_conflict" in codes
    assert r.canonical == "https://example.com/"
    assert r.canonical_urls == [
        "https://example.com/",
        "https://example.com/home",
    ]


def test_ignores_duplicate_canonical_to_same_url():
    # The same URL written relatively vs absolutely is NOT a conflict.
    r = analyze_html(SAMPLE_CANON_DUP, "https://example.com")
    codes = [i.code for i in r.issues]
    assert "canonical_conflict" not in codes
    assert r.canonical_urls == ["https://example.com/"]


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


SAMPLE_METADATA_LINKS = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Metadata links over http</title>
<link rel="canonical" href="http://example.com/">
<link rel="alternate" hreflang="de" href="http://example.com/de">
<link rel="alternate" hreflang="x-default" href="http://example.com/">
<link rel="prev" href="http://example.com/page/1">
<link rel="next" href="http://example.com/page/3">
<link rel="preconnect" href="http://cdn.example.com">
<link rel="dns-prefetch" href="http://cdn.example.com">
<link rel="author" href="http://example.com/about">
<link href="http://example.com/no-rel">
</head><body><h1>Hi</h1></body></html>"""


def test_metadata_links_are_not_mixed_content():
    # None of these <link> rel values make the browser fetch a subresource, so
    # an http:// href on them must never be reported as mixed content.
    r = analyze_html(SAMPLE_METADATA_LINKS, "https://example.com")
    assert r.mixed_content == []
    assert "mixed_content" not in [i.code for i in r.issues]
    # the tags are still parsed normally — we skipped them only for the
    # mixed-content check, we did not stop reading them
    assert r.canonical == "http://example.com/"
    assert len(r.hreflang) == 2


def test_fetching_link_rels_are_still_flagged_as_mixed_content():
    r = analyze_html(
        '<html lang="en"><head><meta charset="utf-8"><title>fetching rels</title>'
        '<link rel="stylesheet" href="http://cdn.example.com/style.css">'
        '<link rel="shortcut icon" href="http://cdn.example.com/favicon.ico">'
        '<link rel="preload" as="font" href="http://cdn.example.com/f.woff2">'
        '<link rel="manifest" href="http://cdn.example.com/app.webmanifest">'
        # not fetched by the browser -> must not be counted
        '<link rel="canonical" href="http://example.com/">'
        '</head><body><h1>Hi</h1></body></html>',
        "https://example.com",
    )
    assert "mixed_content" in [i.code for i in r.issues]
    urls = [m["url"] for m in r.mixed_content]
    assert len(urls) == 4
    assert "http://example.com/" not in urls
    assert all(m["tag"] == "link" and m["attr"] == "href" for m in r.mixed_content)


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


def test_percent_encoded_anchor_matches_literal_id():
    # Static-site generators (MkDocs, Docusaurus, GitBook, ...) write non-ASCII
    # heading anchors percent-encoded in the href while the target id stays as
    # literal text. Browsers decode the fragment before matching, so these are
    # NOT broken — flagging them was a false positive on CJK/i18n docs sites.
    good = analyze_html(
        '<html lang="zh"><head><meta charset="utf-8"><title>ok</title></head>'
        '<body><h1>Hi</h1>'
        '<a href="#%E5%BF%AB%E9%80%9F%E5%BC%80%E5%A7%8B">快速开始</a>'
        '<a href="#caf%C3%A9">Café section</a>'
        '<h2 id="快速开始">快速开始</h2>'
        '<h2 id="café">Café</h2>'
        '</body></html>',
        "https://example.com/docs",
    )
    assert good.broken_anchors == []
    assert "broken_anchors" not in [i.code for i in good.issues]


def test_percent_encoded_anchor_still_flagged_when_target_missing():
    # Decoding must not hide *real* breakage: an encoded fragment whose decoded
    # form matches nothing is still broken, and repeated occurrences of the
    # same target (encoded or literal) are de-duplicated into one record.
    bad = analyze_html(
        '<html lang="zh"><head><meta charset="utf-8"><title>ok</title></head>'
        '<body><h1>Hi</h1>'
        '<a href="#%E4%B8%8D%E5%AD%98%E5%9C%A8">missing encoded</a>'
        '<a href="#不存在">missing literal duplicate</a>'
        '<h2 id="快速开始">快速开始</h2>'
        '</body></html>',
        "https://example.com/docs",
    )
    assert len(bad.broken_anchors) == 1
    assert bad.broken_anchors[0]["href"] == "#%E4%B8%8D%E5%AD%98%E5%9C%A8"
    assert "broken_anchors" in [i.code for i in bad.issues]


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




# --- <html lang> value validity + agreement with hreflang (i18n) ---
# Declaring *a* lang is not enough: a malformed tag is ignored outright, and a
# lang that contradicts the page's own hreflang entry means browsers/screen
# readers and search engines infer different languages for the same page.
def test_flags_invalid_html_lang_value():
    html = (
        '<html lang="english"><head><meta charset="utf-8">'
        "<title>Invalid Language Tag Demo Page</title>"
        "</head><body><h1>Hi</h1></body></html>"
    )
    r = analyze_html(html, "https://example.com/")
    assert r.html_lang == "english"
    assert r.lang_valid is False
    assert "lang_invalid" in [i.code for i in r.issues]
    # presence is still detected, so lang_missing must NOT also fire
    assert "lang_missing" not in [i.code for i in r.issues]


def test_accepts_bcp47_lang_and_hreflang_with_script_subtag():
    # zh-Hans / zh-Hant are valid BCP 47 tags (language + ISO 15924 script) and
    # are widely used on Chinese sites — flagging them would be a false positive
    html = (
        '<html lang="zh-Hans"><head><meta charset="utf-8">'
        "<title>Script Subtag Language Tag Demo</title>"
        '<link rel="alternate" hreflang="zh-Hans" href="https://example.com/">'
        '<link rel="alternate" hreflang="zh-Hant-TW" href="https://example.com/tw">'
        "</head><body><h1>Hi</h1></body></html>"
    )
    r = analyze_html(html, "https://example.com/")
    assert r.lang_valid is True
    codes = [i.code for i in r.issues]
    assert "lang_invalid" not in codes
    assert "hreflang_invalid" not in codes
    assert r.invalid_hreflang == []


def test_flags_lang_hreflang_language_mismatch():
    # the /de page tells search engines it is German (self-referencing
    # hreflang="de") but tells browsers it is English (<html lang="en">)
    html = (
        '<html lang="en"><head><meta charset="utf-8">'
        "<title>Language Mismatch Demonstration Page</title>"
        '<link rel="alternate" hreflang="de" href="https://example.com/de">'
        '<link rel="alternate" hreflang="fr" href="https://example.com/fr">'
        "</head><body><h1>Hallo</h1></body></html>"
    )
    r = analyze_html(html, "https://example.com/de")
    assert r.hreflang_self_ref is True
    assert r.lang_hreflang_mismatch is True
    issue = next(i for i in r.issues if i.code == "lang_hreflang_mismatch")
    assert "de" in issue.message and issue.fix


def test_no_mismatch_when_only_region_differs():
    # "en-US" vs "en-GB" is a region difference, not a language conflict —
    # flagging it would be a false positive
    html = (
        '<html lang="en-US"><head><meta charset="utf-8">'
        "<title>Region Only Difference Demo Page</title>"
        '<link rel="alternate" hreflang="en-GB" href="https://example.com/uk">'
        '<link rel="alternate" hreflang="x-default" href="https://example.com/">'
        "</head><body><h1>Hi</h1></body></html>"
    )
    r = analyze_html(html, "https://example.com/uk")
    assert r.lang_hreflang_mismatch is False
    assert "lang_hreflang_mismatch" not in [i.code for i in r.issues]


def test_lang_checks_not_applicable_without_lang_or_self_hreflang():
    # no lang attribute at all -> validity check is N/A (None), never flagged
    r_bad = analyze_html(SAMPLE_BAD, "https://example.com")
    assert r_bad.lang_valid is None
    assert r_bad.lang_hreflang_mismatch is None
    assert "lang_invalid" not in [i.code for i in r_bad.issues]
    # SAMPLE_GOOD self-references only via x-default (no language to compare),
    # so the mismatch check stays N/A instead of guessing
    r_good = analyze_html(SAMPLE_GOOD, "https://example.com")
    assert r_good.lang_valid is True
    assert r_good.lang_hreflang_mismatch is None
    assert "lang_hreflang_mismatch" not in [i.code for i in r_good.issues]


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


# --- word counting for scripts that do not use spaces -----------------------
# 23 CJK characters + a full-width period. Chinese text has no word separators,
# so a naive whitespace split scores a whole article as a single "word".
_CN_SENTENCE = "国际化站点的搜索引擎优化需要持续投入与细致检查。"

SAMPLE_CN_RICH = (
    '<!doctype html>\n<html lang="zh-Hans"><head><meta charset="utf-8">\n'
    "<title>中文长文示例</title></head>\n<body><h1>产品介绍</h1><p>"
    + _CN_SENTENCE * 30
    + "</p></body></html>"
)


def test_counts_cjk_text_as_words_instead_of_false_thin_content():
    r = analyze_html(SAMPLE_CN_RICH, "https://example.com/zh")
    # 23 chars * 30 sentences + 4 chars in the <h1> = 694 CJK characters,
    # converted at ~1.7 chars per word -> 408 equivalent words.
    assert r.word_count == 408
    assert r.word_count > THIN_CONTENT_MIN_WORDS
    # a full-length Chinese article must NOT be reported as thin content
    assert "thin_content" not in [i.code for i in r.issues]


def test_counts_japanese_and_still_flags_a_genuinely_thin_cjk_page():
    jp_sentence = "国際化サイトの検索エンジン最適化には継続的な改善が必要です。"
    rich_jp = (
        '<!doctype html>\n<html lang="ja"><head><meta charset="utf-8">\n'
        "<title>日本語のサンプル</title></head>\n<body><h1>概要</h1><p>"
        + jp_sentence * 25
        + "</p></body></html>"
    )
    r_rich = analyze_html(rich_jp, "https://example.com/ja")
    # kana and kanji both count: 29 chars * 25 + 2 in the <h1> = 727 -> 428
    assert r_rich.word_count == 428
    assert "thin_content" not in [i.code for i in r_rich.issues]

    # the fix must not silence the check: a genuinely short CJK page is still
    # flagged, so thin-content detection keeps working for Chinese sites
    thin_cn = (
        '<!doctype html>\n<html lang="zh-Hans"><head><meta charset="utf-8">\n'
        "<title>短页</title></head>\n<body><h1>短页</h1><p>内容不多。</p>"
        "</body></html>"
    )
    r_thin = analyze_html(thin_cn, "https://example.com/zh/short")
    assert r_thin.word_count == 4  # 6 CJK chars / 1.7, rounded
    assert "thin_content" in [i.code for i in r_thin.issues]


def test_word_count_handles_mixed_scripts_thai_and_punctuation():
    from globe_lens_mcp.analyzer import THAI_CHARS_PER_WORD, _count_words

    # mixed-language page: Latin words and CJK characters both contribute
    assert _count_words("Hello world 你好世界") == 4  # 2 + round(4 / 1.7)

    # Thai is space-free too, but its words are longer, so it uses its own ratio
    thai = "การเพิ่มประสิทธิภาพเว็บไซต์"  # 27 characters
    assert _count_words(thai * 20) == round(len(thai) * 20 / THAI_CHARS_PER_WORD)

    # punctuation-only tokens are not content in any language
    assert _count_words("| - • 。、") == 0
    assert _count_words("   ") == 0

    # regression guard: plain ASCII counting is unchanged
    assert _count_words("one two three") == 3


SAMPLE_META_REFRESH = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="0; url=/en/">
  <title>Redirecting…</title>
</head>
<body><h1>Redirecting</h1></body>
</html>"""


def test_flags_meta_refresh_redirect_and_resolves_target():
    r = analyze_html(SAMPLE_META_REFRESH, "https://example.com/old")
    codes = [i.code for i in r.issues]
    assert "meta_refresh_redirect" in codes
    # a redirect is not a self-reload; only one of the two may fire
    assert "meta_refresh_reload" not in codes
    assert r.meta_refresh == "0; url=/en/"
    assert r.meta_refresh_delay == 0
    # relative targets are resolved against the page URL, like every other link
    assert r.meta_refresh_url == "https://example.com/en/"
    issue = next(i for i in r.issues if i.code == "meta_refresh_redirect")
    assert "https://example.com/en/" in issue.message
    assert "301" in issue.fix


def test_flags_timed_self_reload_and_parses_quoted_uppercase_target():
    # no url= : the page just reloads itself on a timer (WCAG 2.2.1)
    reload_html = (
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        '<meta http-equiv="Refresh" content="30">'
        "<title>Live dashboard</title></head><body><h1>Stats</h1></body></html>"
    )
    r = analyze_html(reload_html, "https://example.com/dashboard")
    codes = [i.code for i in r.issues]
    assert "meta_refresh_reload" in codes
    assert "meta_refresh_redirect" not in codes
    assert r.meta_refresh_delay == 30
    assert r.meta_refresh_url is None

    # real pages write the target quoted and the key uppercased
    quoted = (
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        "<meta http-equiv=\"refresh\" content=\"5;URL='https://example.com/de/'\">"
        "<title>Weiterleitung</title></head><body><h1>Hi</h1></body></html>"
    )
    r2 = analyze_html(quoted, "https://example.com/")
    assert r2.meta_refresh_delay == 5
    assert r2.meta_refresh_url == "https://example.com/de/"
    assert "meta_refresh_redirect" in [i.code for i in r2.issues]


def test_no_meta_refresh_is_not_flagged_and_content_type_is_untouched():
    r = analyze_html(SAMPLE_GOOD, "https://example.com")
    codes = [i.code for i in r.issues]
    assert "meta_refresh_redirect" not in codes
    assert "meta_refresh_reload" not in codes
    assert r.meta_refresh is None
    assert r.meta_refresh_url is None

    # the neighbouring http-equiv lookup must not be confused by this check:
    # a legacy Content-Type declaration is still read as a charset, not as a
    # refresh, and junk content is ignored rather than guessed into a redirect
    legacy = (
        '<!doctype html>\n<html lang="en"><head>'
        '<meta http-equiv="Content-Type" content="text/html; charset=gb2312">'
        '<meta http-equiv="refresh" content="not a refresh directive">'
        "<title>Legacy</title></head><body><h1>Hi</h1></body></html>"
    )
    r2 = analyze_html(legacy, "https://example.com/legacy")
    assert r2.charset == "gb2312"
    assert r2.meta_refresh is None
    assert not [i.code for i in r2.issues if i.code.startswith("meta_refresh")]
