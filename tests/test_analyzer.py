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
