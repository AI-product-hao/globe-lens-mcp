"""Tests for the GlobeLens MCP server tools (parameter plumbing, no real network).

We stub httpx.AsyncClient with a MockTransport so the request options
(timeout, user_agent, verify_ssl) can be asserted without hitting the network.
"""
import asyncio
from unittest.mock import patch

import httpx

from globe_lens_mcp import server

# Capture the real client class before any patching, so the stub can construct
# a genuine AsyncClient backed by a MockTransport (no recursion into the mock).
REAL_CLIENT = httpx.AsyncClient

SAMPLE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Options Test</title></head><body><h1>Hi</h1></body></html>"""


def _fwd_kwargs(kwargs: dict) -> dict:
    return {k: v for k, v in kwargs.items()
            if k in ("headers", "timeout", "verify", "follow_redirects")}


def test_audit_url_forwards_custom_options():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["ua"] = request.headers.get("user-agent")
        return httpx.Response(200, text=SAMPLE)

    def make_client(*args, **kwargs):
        captured["kwargs"] = kwargs
        return REAL_CLIENT(transport=httpx.MockTransport(handler), **_fwd_kwargs(kwargs))

    with patch.object(server.httpx, "AsyncClient", side_effect=make_client):
        result = asyncio.run(server.audit_url(
            "https://example.com",
            timeout=5,
            user_agent="CustomBot/2.0",
            verify_ssl=False,
        ))

    assert captured["ua"] == "CustomBot/2.0"
    assert captured["kwargs"]["timeout"] == 5
    assert captured["kwargs"]["verify"] is False
    assert result["url"] == "https://example.com"
    assert result["html_lang"] == "en"
    # robots.txt / sitemap.xml were also fetched through the same client
    assert result["has_robots_txt"] in (True, False, None)


def test_audit_url_defaults_to_builtin_user_agent():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["ua"] = request.headers.get("user-agent")
        return httpx.Response(200, text=SAMPLE)

    def make_client(*args, **kwargs):
        return REAL_CLIENT(transport=httpx.MockTransport(handler), **_fwd_kwargs(kwargs))

    with patch.object(server.httpx, "AsyncClient", side_effect=make_client):
        asyncio.run(server.audit_url("https://example.com"))

    assert captured["ua"].startswith("GlobeLens/")


def test_check_i18n_forwards_custom_user_agent():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["ua"] = request.headers.get("user-agent")
        return httpx.Response(200, text=SAMPLE)

    def make_client(*args, **kwargs):
        return REAL_CLIENT(transport=httpx.MockTransport(handler), **_fwd_kwargs(kwargs))

    with patch.object(server.httpx, "AsyncClient", side_effect=make_client):
        result = asyncio.run(server.check_i18n(
            "https://example.com", user_agent="Mozilla/5.0 (staging)"
        ))

    assert captured["ua"] == "Mozilla/5.0 (staging)"
    assert result["html_lang"] == "en"


def test_check_robots_sitemap_forwards_verify_ssl_false():
    captured: dict = {}

    def make_client(*args, **kwargs):
        captured["kwargs"] = kwargs
        # Always 404 so both robots.txt and sitemap.xml are reported missing.
        return REAL_CLIENT(
            transport=httpx.MockTransport(lambda r: httpx.Response(404)),
            **_fwd_kwargs(kwargs),
        )

    with patch.object(server.httpx, "AsyncClient", side_effect=make_client):
        result = asyncio.run(server.check_robots_sitemap(
            "https://example.com", timeout=10, verify_ssl=False
        ))

    assert captured["kwargs"]["timeout"] == 10
    assert captured["kwargs"]["verify"] is False
    assert result["robots_txt"]["found"] is False
    assert result["sitemap_xml"]["found"] is False


def test_audit_url_decodes_non_ascii_content():
    # Real-world (non-English) pages are full of multi-byte UTF-8; the body is
    # returned as raw bytes, so decoding must not mangle accents.
    body = (
        '<!doctype html><html lang="es"><head><meta charset="utf-8">'
        "<title>Café y Niño — Añadir</title></head>"
        "<body><h1>Hola</h1></body></html>"
    ).encode("utf-8")

    def make_client(*args, **kwargs):
        return REAL_CLIENT(
            transport=httpx.MockTransport(lambda r: httpx.Response(200, content=body)),
            **_fwd_kwargs(kwargs),
        )

    with patch.object(server.httpx, "AsyncClient", side_effect=make_client):
        result = asyncio.run(server.audit_url("https://example.com"))

    assert result["html_lang"] == "es"
    assert "Café" in result["title"]
    assert "ñ" in result["title"]


def test_audit_url_truncates_oversized_page():
    # A body larger than MAX_HTML_BYTES must be truncated (and flagged) instead
    # of blowing up the parser or the agent's context window.
    chunk = (
        b'<html lang="en"><head><meta charset="utf-8">'
        b"<title>Big</title></head><body><h1>x</h1></body></html>"
    )
    big = chunk * (2 * 1024 * 1024 // len(chunk) + 50)

    def make_client(*args, **kwargs):
        return REAL_CLIENT(
            transport=httpx.MockTransport(lambda r: httpx.Response(200, content=big)),
            **_fwd_kwargs(kwargs),
        )

    with patch.object(server.httpx, "AsyncClient", side_effect=make_client):
        result = asyncio.run(server.audit_url("https://example.com"))

    codes = [i["code"] for i in result["issues"]]
    assert "page_truncated" in codes


def test_check_i18n_reports_truncation_flag():
    chunk = (
        b'<html lang="en"><head><meta charset="utf-8">'
        b"<title>Big</title></head><body><h1>x</h1></body></html>"
    )
    big = chunk * (2 * 1024 * 1024 // len(chunk) + 50)

    def make_client(*args, **kwargs):
        return REAL_CLIENT(
            transport=httpx.MockTransport(lambda r: httpx.Response(200, content=big)),
            **_fwd_kwargs(kwargs),
        )

    with patch.object(server.httpx, "AsyncClient", side_effect=make_client):
        result = asyncio.run(server.check_i18n("https://example.com"))

    assert result["truncated"] is True


def test_audit_url_respects_custom_max_bytes():
    # An agent auditing a page it knows is huge can lower the cap to keep the
    # audit fast; truncation must kick in at the custom limit, not the 2 MiB
    # default, and still be flagged.
    filler = b"<p>word </p>" * 4000  # ~48 KB, far below the default cap
    body = (
        b'<html lang="en"><head><meta charset="utf-8">'
        b"<title>Big-ish</title></head><body><h1>x</h1>" + filler
        + b"</body></html>"
    )

    def make_client(*args, **kwargs):
        return REAL_CLIENT(
            transport=httpx.MockTransport(lambda r: httpx.Response(200, content=body)),
            **_fwd_kwargs(kwargs),
        )

    with patch.object(server.httpx, "AsyncClient", side_effect=make_client):
        result = asyncio.run(server.audit_url("https://example.com", max_bytes=2048))

    codes = [i["code"] for i in result["issues"]]
    assert "page_truncated" in codes
    # the head fits inside 2 KiB, so core fields still parse
    assert result["html_lang"] == "en"


def test_audit_url_clamps_max_bytes_to_floor():
    # Absurdly small caps (e.g. 10 bytes) would leave nothing parseable; the
    # server clamps to MIN_HTML_BYTES so a normal small page is NOT truncated.
    assert len(SAMPLE.encode()) < server.MIN_HTML_BYTES

    def make_client(*args, **kwargs):
        return REAL_CLIENT(
            transport=httpx.MockTransport(lambda r: httpx.Response(200, text=SAMPLE)),
            **_fwd_kwargs(kwargs),
        )

    with patch.object(server.httpx, "AsyncClient", side_effect=make_client):
        result = asyncio.run(server.audit_url("https://example.com", max_bytes=10))

    codes = [i["code"] for i in result["issues"]]
    assert "page_truncated" not in codes
    assert result["title"] == "Options Test"


def test_check_i18n_respects_custom_max_bytes():
    body = b'<html lang="en"><head><meta charset="utf-8"><title>T</title></head>' \
           b"<body>" + b"<p>word</p>" * 4000 + b"</body></html>"

    def make_client(*args, **kwargs):
        return REAL_CLIENT(
            transport=httpx.MockTransport(lambda r: httpx.Response(200, content=body)),
            **_fwd_kwargs(kwargs),
        )

    with patch.object(server.httpx, "AsyncClient", side_effect=make_client):
        result = asyncio.run(server.check_i18n("https://example.com", max_bytes=2048))

    assert result["truncated"] is True
    assert result["html_lang"] == "en"


def test_audit_url_returns_structured_error_on_404():
    # A 404 (or any non-2xx) must become a parseable error dict, not an
    # unhandled exception that loses the whole tool call for the agent.
    def make_client(*args, **kwargs):
        return REAL_CLIENT(
            transport=httpx.MockTransport(lambda r: httpx.Response(404)),
            **_fwd_kwargs(kwargs),
        )

    with patch.object(server.httpx, "AsyncClient", side_effect=make_client):
        result = asyncio.run(server.audit_url("https://example.com/missing"))

    assert result["ok"] is False
    assert result["status_code"] == 404
    assert result["url"] == "https://example.com/missing"
    assert "error" in result
    # no partial report should leak out alongside the error
    assert "html_lang" not in result


def test_audit_url_returns_structured_error_on_network_failure():
    # DNS / timeout / connection errors must also be caught and returned.
    def make_client(*args, **kwargs):
        def boom(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Name or service not known")
        return REAL_CLIENT(
            transport=httpx.MockTransport(boom),
            **_fwd_kwargs(kwargs),
        )

    with patch.object(server.httpx, "AsyncClient", side_effect=make_client):
        result = asyncio.run(server.audit_url("https://nope.invalid"))

    assert result["ok"] is False
    assert result["status_code"] is None
    assert "error" in result


def test_check_i18n_returns_structured_error_on_404():
    def make_client(*args, **kwargs):
        return REAL_CLIENT(
            transport=httpx.MockTransport(lambda r: httpx.Response(404)),
            **_fwd_kwargs(kwargs),
        )

    with patch.object(server.httpx, "AsyncClient", side_effect=make_client):
        result = asyncio.run(server.check_i18n("https://example.com/missing"))

    assert result["ok"] is False
    assert result["status_code"] == 404
    assert "error" in result


# ---------------------------------------------------------------------------
# Redirect handling: analyze against the FINAL url, not the requested one.
# ---------------------------------------------------------------------------

REDIRECT_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>English Home</title>
<link rel="canonical" href="/en/">
<link rel="alternate" hreflang="en" href="/en/">
<link rel="alternate" hreflang="de" href="/de/">
</head><body><h1>Hello</h1></body></html>"""


def _redirecting_transport(requests_seen: list):
    """example.com/old -> 301 -> example.com/en/ ; robots/sitemap 404."""

    def handler(request: httpx.Request) -> httpx.Response:
        requests_seen.append(str(request.url))
        if request.url.path == "/old":
            return httpx.Response(301, headers={"location": "https://example.com/en/"})
        if request.url.path == "/en/":
            return httpx.Response(200, text=REDIRECT_PAGE)
        return httpx.Response(404)

    return httpx.MockTransport(handler)


def test_audit_url_analyzes_against_final_url_after_redirect():
    # The body belongs to /en/ (the final URL). Relative canonical/hreflang
    # must resolve against it, and the self-referencing hreflang check must
    # pass — comparing against the *requested* /old would wrongly fail it.
    seen: list = []

    def make_client(*args, **kwargs):
        return REAL_CLIENT(transport=_redirecting_transport(seen), **_fwd_kwargs(kwargs))

    with patch.object(server.httpx, "AsyncClient", side_effect=make_client):
        result = asyncio.run(server.audit_url("https://example.com/old"))

    assert result["url"] == "https://example.com/old"  # what the caller asked
    assert result["final_url"] == "https://example.com/en/"
    assert result["redirected"] is True
    assert result["canonical_url"] == "https://example.com/en/"
    assert result["hreflang_self_ref"] is True
    codes = [i["code"] for i in result["issues"]]
    assert "hreflang_no_self_ref" not in codes


def test_audit_url_reports_no_redirect_for_direct_hit():
    def make_client(*args, **kwargs):
        return REAL_CLIENT(
            transport=httpx.MockTransport(lambda r: httpx.Response(200, text=SAMPLE)),
            **_fwd_kwargs(kwargs),
        )

    with patch.object(server.httpx, "AsyncClient", side_effect=make_client):
        result = asyncio.run(server.audit_url("https://example.com"))

    assert result["redirected"] is False
    assert result["final_url"] == "https://example.com"


def test_check_i18n_exposes_final_url_after_redirect():
    seen: list = []

    def make_client(*args, **kwargs):
        return REAL_CLIENT(transport=_redirecting_transport(seen), **_fwd_kwargs(kwargs))

    with patch.object(server.httpx, "AsyncClient", side_effect=make_client):
        result = asyncio.run(server.check_i18n("https://example.com/old"))

    assert result["url"] == "https://example.com/old"
    assert result["final_url"] == "https://example.com/en/"
    assert result["redirected"] is True
    assert result["hreflang_self_ref"] is True
    codes = [i["code"] for i in result["issues"]]
    assert "hreflang_no_self_ref" not in codes


# ---------------------------------------------------------------------------
# follow_redirects=False: inspect the URL itself instead of its destination.
# ---------------------------------------------------------------------------


def test_audit_url_reports_redirect_without_following():
    # Migration QA: the agent wants to know *that* /old redirects and *where*
    # to — following the hop would silently audit the destination instead and
    # hide the status code (301 vs 302 is a real SEO difference).
    seen: list = []

    def make_client(*args, **kwargs):
        return REAL_CLIENT(transport=_redirecting_transport(seen), **_fwd_kwargs(kwargs))

    with patch.object(server.httpx, "AsyncClient", side_effect=make_client):
        result = asyncio.run(server.audit_url(
            "https://example.com/old", follow_redirects=False
        ))

    assert result["ok"] is True
    assert result["status_code"] == 301
    assert result["redirect_to"] == "https://example.com/en/"
    assert result["followed_redirects"] is False
    assert result["redirected"] is False
    # the hop was NOT taken, and no page report leaks out
    assert seen == ["https://example.com/old"]
    assert "html_lang" not in result
    assert "score" not in result


def test_audit_url_resolves_relative_redirect_location():
    # Location headers are frequently relative ("/en/"); the agent should get
    # an absolute target it can audit directly, not a bare path.
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "/en/"})

    def make_client(*args, **kwargs):
        return REAL_CLIENT(transport=httpx.MockTransport(handler), **_fwd_kwargs(kwargs))

    with patch.object(server.httpx, "AsyncClient", side_effect=make_client):
        result = asyncio.run(server.audit_url(
            "https://example.com/de/old", follow_redirects=False
        ))

    assert result["status_code"] == 302
    assert result["redirect_to"] == "https://example.com/en/"


def test_robots_probe_still_follows_redirects_when_page_does_not():
    # follow_redirects=False is about the *page*. Crawlers follow robots.txt
    # redirects (http -> https, apex -> www), so a redirecting robots.txt must
    # still be reported as present — otherwise the option would introduce a
    # false "missing robots.txt".
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            if request.url.host == "www.example.com":
                return httpx.Response(200, text="User-agent: *")
            return httpx.Response(301, headers={
                "location": "https://www.example.com/robots.txt"})
        if request.url.path == "/sitemap.xml":
            return httpx.Response(404)
        return httpx.Response(200, text=SAMPLE)

    def make_client(*args, **kwargs):
        return REAL_CLIENT(transport=httpx.MockTransport(handler), **_fwd_kwargs(kwargs))

    with patch.object(server.httpx, "AsyncClient", side_effect=make_client):
        result = asyncio.run(server.audit_url(
            "https://example.com/", follow_redirects=False
        ))

    assert result["followed_redirects"] is False
    assert result["has_robots_txt"] is True   # redirected robots.txt still found
    assert result["has_sitemap"] is False
    assert result["title"] == "Options Test"  # the page itself was audited


def test_check_i18n_reports_redirect_without_following():
    # Locale routing QA: does "/" really forward to "/en/"?
    seen: list = []

    def make_client(*args, **kwargs):
        return REAL_CLIENT(transport=_redirecting_transport(seen), **_fwd_kwargs(kwargs))

    with patch.object(server.httpx, "AsyncClient", side_effect=make_client):
        result = asyncio.run(server.check_i18n(
            "https://example.com/old", follow_redirects=False
        ))

    assert result["ok"] is True
    assert result["status_code"] == 301
    assert result["redirect_to"] == "https://example.com/en/"
    assert result["followed_redirects"] is False
    assert "hreflang" not in result


def test_following_redirects_stays_the_default():
    # Backwards compatibility: callers that omit the flag keep the old
    # behaviour (hop followed, destination audited).
    seen: list = []

    def make_client(*args, **kwargs):
        return REAL_CLIENT(transport=_redirecting_transport(seen), **_fwd_kwargs(kwargs))

    with patch.object(server.httpx, "AsyncClient", side_effect=make_client):
        result = asyncio.run(server.audit_url("https://example.com/old"))

    assert result["followed_redirects"] is True
    assert result["final_url"] == "https://example.com/en/"
    assert "redirect_to" not in result


# --- lang validity / lang-vs-hreflang agreement surfaced by check_i18n ---
LANG_CONFLICT_PAGE = """<!doctype html>
<html lang="english"><head><meta charset="utf-8">
<title>Lang Conflict</title>
<link rel="alternate" hreflang="de" href="https://example.com/de">
</head><body><h1>Hallo</h1></body></html>"""


def test_check_i18n_exposes_lang_validity_and_related_issues():
    def make_client(*args, **kwargs):
        return REAL_CLIENT(
            transport=httpx.MockTransport(
                lambda r: httpx.Response(200, text=LANG_CONFLICT_PAGE)
            ),
            **_fwd_kwargs(kwargs),
        )

    with patch.object(server.httpx, "AsyncClient", side_effect=make_client):
        result = asyncio.run(server.check_i18n("https://example.com/de"))

    assert result["html_lang"] == "english"
    assert result["lang_valid"] is False
    # lang is invalid, so the language comparison is skipped rather than guessed
    assert result["lang_hreflang_mismatch"] is None
    # the issue filter must let lang_* codes through, not just hreflang*
    assert "lang_invalid" in [i["code"] for i in result["issues"]]


# ---------------------------------------------------------------------------
# robots.txt / sitemap.xml probes: a 200 is not proof the file exists.
# ---------------------------------------------------------------------------

SPA_FALLBACK = (
    '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
    "<title>My App</title></head><body><div id=\"root\"></div></body></html>"
)

REAL_ROBOTS = "User-agent: *\nDisallow: /admin\nSitemap: https://example.com/sitemap.xml\n"

REAL_SITEMAP = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    "<url><loc>https://example.com/</loc></url></urlset>"
)


def _spa_host_transport():
    """Catch-all rewrite: every unknown path answers 200 with index.html."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path in ("/robots.txt", "/sitemap.xml"):
            return httpx.Response(
                200, text=SPA_FALLBACK, headers={"content-type": "text/html"}
            )
        return httpx.Response(200, text=SAMPLE)

    return httpx.MockTransport(handler)


def test_audit_url_rejects_spa_fallback_html_as_robots_and_sitemap():
    # Vercel/Netlify/CF Pages serve index.html for any unknown path. Trusting
    # the status code alone told the agent both files exist, hiding a real SEO
    # gap on exactly the kind of site this tool is built for.
    def make_client(*args, **kwargs):
        return REAL_CLIENT(transport=_spa_host_transport(), **_fwd_kwargs(kwargs))

    with patch.object(server.httpx, "AsyncClient", side_effect=make_client):
        result = asyncio.run(server.audit_url("https://example.com/"))

    assert result["has_robots_txt"] is False
    assert result["has_sitemap"] is False
    assert result["title"] == "Options Test"  # the page itself still audited


def test_check_robots_sitemap_unmasks_soft_200_and_reports_status():
    def make_client(*args, **kwargs):
        return REAL_CLIENT(transport=_spa_host_transport(), **_fwd_kwargs(kwargs))

    with patch.object(server.httpx, "AsyncClient", side_effect=make_client):
        result = asyncio.run(server.check_robots_sitemap("https://example.com"))

    assert result["robots_txt"]["found"] is False
    assert result["sitemap_xml"]["found"] is False
    # the status code is surfaced so the agent can see it was a soft 200
    assert result["robots_txt"]["status_code"] == 200
    assert result["sitemap_xml"]["status_code"] == 200


def test_check_robots_sitemap_accepts_genuine_files():
    # The sniffing must not swing into false negatives: real files, including
    # an unusual content type or a sitemap index, still count as present.
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(
                200, text=REAL_ROBOTS, headers={"content-type": "text/plain"}
            )
        return httpx.Response(
            200, text=REAL_SITEMAP, headers={"content-type": "application/xml"}
        )

    def make_client(*args, **kwargs):
        return REAL_CLIENT(transport=httpx.MockTransport(handler), **_fwd_kwargs(kwargs))

    with patch.object(server.httpx, "AsyncClient", side_effect=make_client):
        result = asyncio.run(server.check_robots_sitemap("https://example.com/deep/page"))

    assert result["robots_txt"]["found"] is True
    assert result["sitemap_xml"]["found"] is True


def test_empty_robots_txt_still_counts_as_present():
    # An empty robots.txt is valid (allow everything) — rejecting it would be
    # a false "missing robots.txt".
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="")
        return httpx.Response(404)

    def make_client(*args, **kwargs):
        return REAL_CLIENT(transport=httpx.MockTransport(handler), **_fwd_kwargs(kwargs))

    with patch.object(server.httpx, "AsyncClient", side_effect=make_client):
        result = asyncio.run(server.check_robots_sitemap("https://example.com"))

    assert result["robots_txt"]["found"] is True
    assert result["sitemap_xml"]["found"] is False


def test_check_robots_sitemap_reports_unknown_on_network_error():
    # A DNS/TLS/timeout failure means "unknown", not "missing" — previously it
    # was reported as found=False, telling the agent to create files that may
    # well already exist.
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("dns failure", request=request)

    def make_client(*args, **kwargs):
        return REAL_CLIENT(transport=httpx.MockTransport(handler), **_fwd_kwargs(kwargs))

    with patch.object(server.httpx, "AsyncClient", side_effect=make_client):
        result = asyncio.run(server.check_robots_sitemap("https://nope.invalid"))

    assert result["robots_txt"]["found"] is None
    assert result["sitemap_xml"]["found"] is None
    assert "error" in result["robots_txt"]


def test_check_i18n_exposes_hreflang_cluster_conflicts():
    # The i18n tool must surface the cluster-integrity findings, not just the
    # issue text: an agent needs the structured pairs to rewrite the <link>s.
    page = """<!doctype html>
    <html lang="en"><head><meta charset="utf-8">
    <title>Conflicting alternates demo page</title>
    <link rel="alternate" hreflang="en" href="https://example.com/en">
    <link rel="alternate" hreflang="fr" href="https://example.com/en">
    <link rel="alternate" hreflang="de" href="https://example.com/de">
    <link rel="alternate" hreflang="de" href="https://example.com/de-at">
    </head><body><h1>Hi</h1></body></html>"""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=page)

    def make_client(*args, **kwargs):
        return REAL_CLIENT(transport=httpx.MockTransport(handler), **_fwd_kwargs(kwargs))

    with patch.object(server.httpx, "AsyncClient", side_effect=make_client):
        result = asyncio.run(server.check_i18n("https://example.com/en"))

    assert result["hreflang_conflicts"] == [
        {"hreflang": "de",
         "urls": ["https://example.com/de", "https://example.com/de-at"]}
    ]
    assert result["hreflang_duplicate_urls"] == [
        {"url": "https://example.com/en", "hreflang": ["en", "fr"]}
    ]
    codes = [i["code"] for i in result["issues"]]
    assert "hreflang_conflict" in codes and "hreflang_duplicate_url" in codes
    # every reported issue still ships an actionable fix hint
    assert all(i["fix"] for i in result["issues"])
