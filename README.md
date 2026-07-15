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
  crawl control, **JSON-LD structured data** presence, plus `robots.txt` /
  `sitemap.xml` presence. Returns a **0–100 score** and prioritized issues.
- 🌐 **i18n focus** (`check_i18n`): html `lang`, `hreflang` alternates, `x-default`.
- 🤖 **Crawl readiness** (`check_robots_sitemap`): confirms the site is discoverable.
- 🛡️ **Robust by design**: relative `canonical` and `hreflang` links are resolved to
  **absolute URLs** (so an agent can act on them directly), and empty / malformed
  HTML returns a clear `empty_html` error instead of crashing.

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
    { "severity": "warning", "code": "hreflang_no_default",
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
