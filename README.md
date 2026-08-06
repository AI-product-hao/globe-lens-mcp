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
  links** (`href="#frag"` pointing to a missing target), **unsafe external
  `target="_blank"` links** (cross-origin links that open a new tab without
  `rel="noopener noreferrer"` — reverse-tabnabbing / Lighthouse "unsafe
  links"), **thin-content
  detection** (body word count below a healthy threshold, script/style
  boilerplate excluded, and **script-aware**: Chinese, Japanese and Thai text
  has no spaces, so it is measured by character count instead of being scored
  as a single word), **conflicting `canonical` detection** (multiple
  `rel="canonical"` links pointing to *different* URLs — which makes search
  engines ignore the canonical signal entirely; duplicate links resolving to the
  same address are not flagged), **`meta refresh` detection**
  (`<meta http-equiv="refresh" content="0; url=…">` is a client-side redirect
  that should be a real 301 — it is reported with the target resolved to an
  absolute URL, while a *targetless* timed self-reload is flagged separately as
  a WCAG 2.2.1 concern), plus `robots.txt` /
  `sitemap.xml` presence. Returns a **0–100 score** and **issues sorted by
  severity** — each issue carries a numeric `priority` field (`error` > `warning`
  > `info`) **and an actionable `fix` hint** (a concrete remedy such as the
  exact tag to add), so the agent can apply the most urgent fix first without
  researching the rule.
- 🌐 **i18n focus** (`check_i18n`): html `lang`, `hreflang` alternates, `x-default`,
  and **hreflang value validation** — malformed codes like `en_US` (underscore
  instead of hyphen) or `english` are flagged, since search engines silently
  ignore them and the intended alternate is lost. Also checks the
  **self-referencing hreflang** rule: Google requires every page in an hreflang
  cluster to list *itself* as an alternate, otherwise the whole set may be
  ignored — GlobeLens compares resolved, normalized URLs (trailing slash and
  host case insensitive) and reports `hreflang_self_ref` plus a
  `hreflang_no_self_ref` warning when the self-link is missing.
- 🗣️ **Language tag correctness**: `<html lang>` is validated as a real BCP 47
  tag (`lang_valid`), so `english`, `en_US` or `en-USA` are flagged
  (`lang_invalid`) instead of silently ignored by browsers and screen readers;
  script subtags such as `zh-Hans` / `zh-Hant-TW` are accepted for both `lang`
  and `hreflang`. GlobeLens also cross-checks the two signals: if a page's own
  hreflang entry says `de` while `<html lang="en">`, you get a
  `lang_hreflang_mismatch` warning (a region-only difference like `en-US` vs
  `en-GB` is deliberately **not** flagged).
- 🤖 **Crawl readiness** (`check_robots_sitemap`): confirms the site is discoverable —
  and detects **soft 200s**, where an SPA catch-all rewrite serves `index.html`
  for `/robots.txt` and `/sitemap.xml` so the files only *look* like they exist.
  Each result carries `found` (`true` / `false` / `null` when the probe failed)
  plus the raw `status_code`.
- 🛡️ **Robust by design**: relative `canonical` and `hreflang` links are resolved to
  **absolute URLs** (so an agent can act on them directly), and empty / malformed
  HTML returns a clear `empty_html` error instead of crashing. Charset detection
  accepts **both** the HTML5 `<meta charset>` and the legacy
  `<meta http-equiv="Content-Type" content="…; charset=…">` form, so older /
  non-English pages are no longer falsely flagged as missing a charset. In-page
  anchor checking **percent-decodes fragments before matching** (browsers do the
  same), so encoded non-ASCII anchors like `href="#%E5%BF%AB%E9%80%9F%E5%BC%80%E5%A7%8B"`
  targeting `id="快速开始"` — the norm on CJK/i18n docs sites — are not falsely
  reported as broken. Word counting is **script-aware** for the same reason: a
  full-length Chinese or Japanese article is no longer mistaken for a two-word
  page and flagged as thin content. Mixed-content scanning only looks at
  `<link>` tags the browser actually **fetches** (`stylesheet`, `icon`,
  `preload`, `manifest`, …), so an `http://` `canonical`, `hreflang` alternate,
  `prev`/`next` or `preconnect` hint is never miscounted as an insecure
  subresource. The `robots.txt` / `sitemap.xml` probes **never trust a bare
  `200`**: hosts with a catch-all rewrite (Vercel, Netlify, Cloudflare Pages —
  most SPA deployments) answer 200 with `index.html` for *every* unknown path,
  so the body is sniffed to confirm it really is the file; and a probe that
  fails (DNS/TLS/timeout) reports `null` — "unknown" — instead of claiming the
  file is missing. GlobeLens
  also decodes **any charset safely** (mis-encoded pages never crash the agent) and
  **truncates oversized pages**, flagging them via a `page_truncated` info issue so
  audits stay fast and bounded. When a target is unreachable, `audit_url` and
  `check_i18n` return a **structured error** (`{"ok": false, "status_code": …,
  "error": …}`) instead of throwing — so the agent can retry / report / skip
  rather than lose the whole tool call. **Redirects are followed and the report
  is computed against the final URL** (relative canonical/hreflang resolution,
  the self-referencing hreflang check, and robots.txt/sitemap.xml probing all
  use the page you actually landed on); `final_url` and `redirected` fields
  tell the agent exactly which page was analyzed.

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
      "message": "No x-default hreflang; recommended for international sites.",
      "fix": "Add <link rel=\"alternate\" hreflang=\"x-default\" href=\"...\"> pointing to the fallback version." }
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
| `max_bytes` | `2097152` (2 MiB) | Cap on the HTML fed to the parser (`audit_url` / `check_i18n`). Raise it to fully audit heavy SPA pages; lower it to keep audits of huge pages fast. Values below 1 KiB are clamped up, and truncation is always flagged (`page_truncated` / `truncated`). |
| `follow_redirects` | `true` | Set `false` to inspect the URL *itself* instead of the page it forwards to (`audit_url` / `check_i18n`). |

```json
{ "url": "https://staging.example.com", "verify_ssl": false, "user_agent": "Mozilla/5.0" }
{ "url": "https://heavy-spa.example.com", "max_bytes": 8388608 }
{ "url": "https://example.com/old-page", "follow_redirects": false }
```

### Inspecting a redirect instead of following it

By default GlobeLens follows redirects and audits the destination (reporting
`final_url` / `redirected`). With `follow_redirects: false` it stops at the
first hop and reports it verbatim — useful to verify a migration really returns
**301** and not 302, or to confirm that `/` forwards to the intended locale
instead of silently auditing whichever language version you land on:

```json
{
  "ok": true,
  "url": "https://example.com/old-page",
  "status_code": 301,
  "redirect_to": "https://example.com/en/new-page",
  "followed_redirects": false
}
```

Relative `Location` headers are resolved to absolute URLs, so the target can be
fed straight back into `audit_url`. The `robots.txt` / `sitemap.xml` probes keep
following redirects (crawlers do too), so this option never produces a false
"missing robots.txt".

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
