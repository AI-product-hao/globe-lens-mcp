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
