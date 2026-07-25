# GlobeLens — SEO & i18n audit MCP server

[![CI](https://github.com/AI-product-hao/globe-lens-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/AI-product-hao/globe-lens-mcp/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**GlobeLens** is an [MCP](https://modelcontextprotocol.io) server that lets your AI
coding agent (Claude, Codex, Cursor, Cline, OpenCode, …) **audit any public website
for SEO and internationalization readiness** — with one tool call.

It is built for **indie developers and small teams going global**, who need to ship
sites that are correct across regions and languages: proper `hreflang`, `lang`
attributes, canonical/robots/sitemap, and clean meta/OG tags.

> 🌍 Born from a real need: most "is my site global-ready?" checks are manual. GlobeLens
> turns them into something an AI agent can run while it writes your code.

## Features

- 🔍 **Full audit** (`audit_url`): title, meta description, `lang`, `hreflang`,
  canonical, viewport, charset, Open Graph / Twitter cards, **H1 structure**
  (missing / multiple), **image `alt` text coverage**, **`meta robots` / noindex**
  crawl control, **JSON-LD structured data** presence, **mixed-content detection**
  (insecure `http://` subresources on HTTPS pages), **broken in-page anchor
  links** (`href="#frag"` pointing to a missing target), **thin-content
  detection** (body word count below a healthy threshold, script/style
  boilerplate excluded), plus `robots.txt` /
  `sitemap.xml` presence. Returns a **0–100 score** and **issues sorted by
  severity** — each issue carries a numeric `priority` field (`error` > `warning`
  > `info`), so the agent can act on the most urgent fix first.
- 🌐 **i18n focus** (`check_i18n`): html `lang`, `hreflang` alternates, `x-default`,
  and **hreflang value validation** — malformed codes like `en_US` (underscore
  instead of hyphen) or `english` are flagged, since search engines silently
  ignore them and the intended alternate is lost. Also checks the
  **self-referencing hreflang** rule: Google requires every page in an hreflang
  cluster to list *itself* as an alternate, otherwise the whole set may be
  ignored — GlobeLens compares resolved, normalized URLs (trailing slash and
  host case insensitive) and reports `hreflang_self_ref` plus a
  `hreflang_no_self_ref` warning when the self-link is missing.
- 🤖 **Crawl readiness** (`check_robots_sitemap`): confirms the site is discoverable.
- 🛡️ **Robust by design**: relative `canonical` and `hreflang` links are resolved to
  **absolute URLs** (so an agent can act on them directly), and empty / malformed
  HTML returns a clear `empty_html` error instead of crashing. Charset detection
  accepts **both** the HTML5 `<meta charset>` and the legacy
  `<meta http-equiv="Content-Type" content="…; charset=…">` form, so older /
  non-English pages are no longer falsely flagged as missing a charset. GlobeLens
  also decodes **any charset safely** (mis-encoded pages never crash the agent) and
  **truncates oversized pages**, flagging them via a `page_truncated` info issue so
  audits stay fast and bounded. When a target is unreachable, `audit_url` and
  `check_i18n` return a **structured error** (`{"ok": false, "status_code": …,
  "error": …}`) instead of throwing — so the agent can retry / report / skip
  rather than lose the whole tool call.

## Install

```bash
pip install globe-lens-mcp
# or
uvx globe-lens-mcp
```

## Wire it into your agent

**Claude Desktop / Codex** — add to your `claude_desktop_config.json` (or equivalent):

```json
{
  "mcpServers": {
    "globe-lens": {
      "command": "uvx",
      "args": ["globe-lens-mcp"]
    }
  }
}
```

Or, if you installed with pip into a venv, point `command` at the executable:

```json
{
  "mcpServers": {
    "globe-lens": {
      "command": "/path/to/venv/bin/globe-lens-mcp"
    }
  }
}
```

## Example

Ask your agent:

> "Audit https://my-site.com for international SEO readiness."

It calls `audit_url` and returns something like:

```json
{
  "url": "https://my-site.com",
  "html_lang": "en",
  "score": 78,
  "issues": [
    { "severity": "warning", "code": "hreflang_no_default", "priority": 2,
      "message": "No x-default hreflang; recommended for international sites." }
  ]
}
```

## Tool options

Every tool accepts optional request controls — handy for staging/preview sites
and for matching how real users or crawlers see your pages:

| Param | Default | Use case |
| --- | --- | --- |
| `timeout` | `20` | Tighten/loosen the request timeout (seconds). |
| `user_agent` | GlobeLens bot | Override the UA to mimic a browser or a specific crawler. |
| `verify_ssl` | `true` | Set `false` to audit staging sites with self-signed certs. |

```json
{ "url": "https://staging.example.com", "verify_ssl": false, "user_agent": "Mozilla/5.0" }
```

## Develop

```bash
git clone https://github.com/AI-product-hao/globe-lens-mcp
cd globe-lens-mcp
python -m venv .venv && source .venv/bin/activate
pip install -e ".[test]"
pytest -q
```

## License

[MIT](LICENSE) © 2026 David Chu
