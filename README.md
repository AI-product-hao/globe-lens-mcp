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
  canonical, viewport (including a **zoom-locked viewport** check —
  `user-scalable=no` / `maximum-scale<=1` is a WCAG 2.5.1 failure that traps
  low-vision users at 100%), charset, Open Graph / Twitter cards, **H1 structure**
  (missing / multiple), **image `alt` text coverage**, **`<img>` missing
  explicit `width`/`height`** (a Cumulative Layout Shift / Core Web Vitals
  concern — without sized images the page jumps as they load), **`meta robots` / noindex**
  crawl control, **JSON-LD structured data** presence, **mixed-content detection**
  (insecure `http://` subresources on HTTPS pages — including `srcset`
  responsive images), **broken in-page anchor
  links** (`href="#frag"` pointing to a missing target), **unsafe external
  `target="_blank"` links** (cross-origin links that open a new tab without
  `rel="noopener noreferrer"` — reverse-tabnabbing / Lighthouse "unsafe
  links"), **thin-content
  detection** (body word count below a healthy threshold, script/style
  boilerplate excluded, and **script-aware**: Chinese, Japanese and Thai text
  has no spaces, so it is measured by character count instead of being scored
  as a single word), **favicon presence** (a missing `<link rel="icon">` is
  flagged as a cheap brand-recognition fix for tabs, bookmarks and search
  results), **duplicate `meta description` detection** (more than one
  `<meta name="description">` tag — CMS/plugin injection makes search engines
  pick one arbitrarily, so your tuned snippet may never show), **conflicting
  `canonical` detection** (multiple
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
  `hreflang_no_self_ref` warning when the self-link is missing. It also catches
  **cluster-integrity breakage**: one `hreflang` value declared against several
  URLs (`hreflang_conflict`) and several values pointing at the *same* URL
  (`hreflang_duplicate_url`) — both make Google silently discard the
  contradictory pairs, so the alternates they were meant to declare vanish.
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
  **absolute URLs** (so an agent can act on them directly), and a page's
  `<base href>` is honored when resolving them — so a CDN-fronted page that
  declares `<base href="https://cdn.example.com/sub/">` and a relative
  `canonical` still yields the correct absolute URL instead of a wrong one;
  empty / malformed
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
  file is missing. The page title is read from the **HTML `<title>` only**: an
  inline `<svg><title>Close menu</title></svg>` icon label is never mistaken
  for the document title, so an SPA shell served without a real `<title>` still
  gets the `title_missing` error it deserves instead of a fictional one.
  Likewise only `<a name="…">` counts as a legacy anchor target — a `name` on a
  `<meta>`, form control or `<iframe>` no longer makes a dead
  `href="#description"` look valid. GlobeLens
  also decodes **any charset safely** (mis-encoded pages never crash the agent) and
  **truncates oversized pages**, flagging them via a `page_truncated` info issue so
  audits stay fast and bounded. When a target is unreachable, `audit_url` and
  `check_i18n` return a **structured error** (`{"ok": false, "status_code": …,
  "error": …}`) instead of throwing — so the agent can retry / report / skip
  rather than lose the whole tool call. An **unfetchable URL** — no scheme
  (`example.com`, `localhost:3000`), a non-http(s) scheme (`file:`, `data:`), a
  missing host, whitespace in the host, or an unparseable value — is rejected
  **before any request** with a specific message and, where obvious, a corrected
  `suggestion` URL (e.g. `https://example.com`); `httpx.InvalidURL` (not a
  `httpx.HTTPError` subclass) is caught as a clean structured error too, so a bad
  argument never surfaces as a stack trace or a fake "site down". **Redirects are
  followed and the report
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

## Real-world walkthrough

Imagine you just shipped a bilingual landing page. Ask your agent:

> "Audit https://my-site.com/es and fix the worst SEO/i18n issues GlobeLens
> reports, starting with the highest-priority one."

The agent calls `audit_url` and gets a prioritized report. A real (abbreviated)
result for a page that forgot its Spanish hreflang cluster:

```json
{
  "url": "https://my-site.com/es",
  "html_lang": "es",
  "score": 71,
  "issues": [
    { "severity": "warning", "code": "hreflang_no_self_ref", "priority": 2,
      "message": "hreflang set does not reference this page itself; Google requires a self-referencing hreflang link…",
      "fix": "Add an hreflang link whose href is this page's own URL to the alternate set." },
    { "severity": "warning", "code": "hreflang_no_default", "priority": 2,
      "message": "No x-default hreflang; recommended for international sites.",
      "fix": "Add <link rel=\"alternate\" hreflang=\"x-default\" href=\"...\"> pointing to the fallback version." },
    { "severity": "info", "code": "og_missing", "priority": 1,
      "message": "Missing Open Graph tags; weak social sharing preview.",
      "fix": "Add <meta property=\"og:title\" …> and <meta property=\"og:description\" …> for social sharing previews." }
  ]
}
```

Because every issue carries a `priority` and an actionable `fix`, the agent
fixes the two `warning`s first (add the self-referencing `es` link + an
`x-default`), then the Open Graph tags — no extra research needed. Re-running
`audit_url` then shows `score` climbing as each fix lands. That loop —
**audit → fix the highest-priority issue → re-audit** — is exactly the
real usage scenario GlobeLens is built for.

## Audit in CI / pre-merge

Because every response carries an `ok` flag and an `error_count` (the number
of `error`-severity issues), GlobeLens drops straight into a pipeline: point it
at a preview / staging URL and **block the merge when an error-severity issue
appears** — no human has to read the report first.

> "Before merging any change that touches our marketing pages, run `audit_url`
> on the preview URL. If `ok` is false or `error_count > 0`, fail the check and
> tell me which issues to fix."

A minimal gate (pseudo-code):

```python
res = await audit_url(preview_url)
if not res["ok"] or res["error_count"] > 0:
    raise SystemExit(f"SEO/i18n gate failed: {res['error_count']} error(s)")
```

Because every issue also carries a `priority` and a copy-paste `fix`, the agent
can both **enforce** the gate *and* **apply** the fix in the same run — the
audit → fix → re-audit loop above, automated. `check_i18n` exposes the same
`ok` / `error_count` over its filtered i18n issues, so a localization gate can
fail on an invalid or missing `<html lang>` without the full-page score
diluting it with unrelated info warnings.

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
| `probe_robots_sitemap` | `true` | Set `false` to skip the two extra `robots.txt` / `sitemap.xml` requests (`audit_url` only). Audit many pages at once, or avoid rate-limiting the host; `has_robots_txt` / `has_sitemap` then come back as `null` ("not checked"). |

```json
{ "url": "https://staging.example.com", "verify_ssl": false, "user_agent": "Mozilla/5.0" }
{ "url": "https://heavy-spa.example.com", "max_bytes": 8388608 }
{ "url": "https://example.com/old-page", "follow_redirects": false }
{ "url": "https://example.com", "probe_robots_sitemap": false }
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
