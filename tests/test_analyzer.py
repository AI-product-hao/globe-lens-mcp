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
