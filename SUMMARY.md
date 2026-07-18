# GlobeLens — 7-Day Maintenance Summary

> Generated on **2026-07-18** after Day 7, as the capstone of a 7-day continuous
> maintenance streak. Purpose: document the project's real, verifiable progress
> and provide ready-to-use material for the **OpenAI Codex for Open Source**
> application (openai.com/form/codex-for-oss).

---

## 1. What GlobeLens is

**GlobeLens** is a Python [MCP](https://modelcontextprotocol.io) server that lets
an AI coding agent (Claude, Codex, Cursor, Cline, OpenCode, …) **audit any public
website for SEO and internationalization (i18n) readiness** with a single tool
call. It is built for indie developers and small teams going global who need to
ship sites that are correct across regions and languages.

- Zero required network access for the core logic (the analyzer is pure
  HTML parsing, fully unit-tested). Network is only used to fetch the URL and
  `robots.txt` / `sitemap.xml`.
- Dependency-light: `beautifulsoup4` + `httpx` + `fastmcp`.
- Every change in this 7-day streak is **unit-tested**, **documented**, and
  **backward-compatible** (no breaking changes, no new required deps).

---

## 2. Tools (3 MCP tools)

| Tool | Signature | What it returns |
| --- | --- | --- |
| `audit_url` | `(url, timeout=20, user_agent=None, verify_ssl=True)` | Full SEO/i18n report: structured fields + a 0–100 score + **issues sorted by severity** (each with a `priority` field). |
| `check_i18n` | `(url, timeout=20, user_agent=None, verify_ssl=True)` | i18n-focused subset: `html_lang`, `hreflang` alternates, `x-default`, filtered+sorted issues, `truncated` flag. |
| `check_robots_sitemap` | `(url, timeout=20, user_agent=None, verify_ssl=True)` | Whether the site exposes `robots.txt` and `sitemap.xml` (presence + fetch error detail). |

All three accept optional `timeout` / `user_agent` / `verify_ssl` for real
staging/preview/self-signed-cert workflows.

---

## 3. Audit dimensions covered by `audit_url`

- **Title** — missing, too short (<30), too long (>60).
- **Meta description** — missing, short (<70), long (>160).
- **`<html lang>`** — missing (error; critical for i18n).
- **Charset** — `meta charset` declared or not.
- **Viewport** — present or not (mobile friendliness).
- **Canonical** — captured verbatim **and** resolved to an absolute `canonical_url`.
- **hreflang** — captured with each entry resolved to an absolute `abs_href`;
  warns when no `x-default`.
- **Open Graph / Twitter cards** — `og:title` / `og:description` presence.
- **`meta robots` / noindex** — parses directives; warns on `noindex`.
- **JSON-LD structured data** — detects `application/ld+json`; info when missing.
- **H1 structure** — missing or multiple (a11y / document structure).
- **Image `alt` coverage** — counts images and those missing `alt`.
- **Mixed content** — plaintext `http://` subresources on HTTPS pages (with
  tag/attr/url for each), correctly ignoring relative & protocol-relative URLs.
- **Truncation signal** — `page_truncated` info when the page exceeded 2 MiB.
- **Degenerate input** — `empty_html` error (score 0) instead of a crash.
- **Crawl readiness** — live `robots.txt` / `sitemap.xml` presence.

### Output quality
Issues are returned **sorted by severity** (error > warning > info) and each
carries a numeric `priority` field, so an agent can act on the most urgent fix
first.

### Robustness (kept deliberately simple & bounded)
- Relative `canonical` / `hreflang` links resolved to absolute URLs.
- Empty / whitespace-only HTML returns a clear error (never crashes).
- Any charset decoded safely (`errors="replace"`); non-English pages never break.
- Oversized pages truncated at 2 MiB with a `page_truncated` flag.

---

## 4. Day-by-day changelog (the evidence trail)

| Day | Date | Category | Change | Tests |
| --- | --- | --- | --- | --- |
| 0 | 2026-07-12 | scaffold | Repo skeleton, 3 tools, 2 tests, MIT, CI | 2 passed |
| 1 | 2026-07-12 | new audit dim | H1 structure + image `alt` coverage | 4 passed |
| 2 | 2026-07-13 | tool options | `timeout` / `user_agent` / `verify_ssl` on all 3 tools | 8 passed |
| 3 | 2026-07-15 | new audit dim | `meta robots`/noindex + JSON-LD detection | 10 passed |
| 4 | 2026-07-15 | robustness | relative→absolute URL resolution + empty-HTML safety | 12 passed |
| 5 | 2026-07-16 | new audit dim | mixed-content detection (HTTPS pages) | 14 passed |
| 6 | 2026-07-17 | robustness | safe charset decoding + oversized-page truncation | 18 passed |
| 7 | 2026-07-18 | issue severity | `priority` field + severity-sorted output (true "prioritized issues") | **20 passed** |

**Novelty discipline:** categories were rotated to avoid two consecutive same-type
changes (new-dimension / options / robustness / severity), and every change shipped
with tests + docs.

---

## 5. Project value statement (draft for the Codex for OSS application)

> **GlobeLens** is a small, focused MCP server that brings website SEO /
> internationalization auditing to AI coding agents. Indie developers going global
> repeatedly hit the same silent failures — missing `hreflang`, no `x-default`,
> `noindex` left in production, plaintext mixed content, undeclared `lang` — that
> tank search visibility across regions. GlobeLens turns these manual, easy-to-skip
> checks into a single tool call an agent can run *while it writes the code*.
>
> What makes it a good fit for Codex for Open Source: it is a real, maintained
> project with a continuous 7-day streak of tested, documented, backward-compatible
> improvements; the core analyzer is network-free and fully unit-tested, so it is
> cheap to keep healthy and easy for contributors to extend; and it serves a clear,
> growing use case (AI agents maintaining production web apps). Codex would help us
> close the remaining gaps faster — broader schema.org coverage, sitemap/robots
> parsing, and richer i18n checks — without sacrificing the test-and-docs discipline
> that keeps the project trustworthy.

---

## 6. ⚠️ Star growth depends on active distribution

A clean commit history and good code **do not** automatically produce stars.
GitHub stars come from **people seeing the project** — which means the maintainer
must actively distribute it. Code quality is the foundation; distribution is what
converts it into visibility. Below are copy-paste drafts for the three channels
most relevant to an English/Chinese dev audience.

### X (Twitter) — draft 1 (launch)

> Shipped GlobeLens 🌍 — an MCP server that lets your AI coding agent audit any
> site for SEO + i18n readiness (hreflang, lang, canonical, noindex, JSON-LD, mixed
> content, image alt…) in one tool call.
>
> Built for indie devs going global. MIT, zero-config.
> 👉 github.com/AI-product-hao/globe-lens-mcp
> #buildinpublic #mcp #seo

### X (Twitter) — draft 2 (proof-of-work angle)

> 7 days, 7 real commits, 20 passing tests. GlobeLens now returns SEO issues
> *sorted by severity* so your agent fixes the urgent stuff first.
> Small, tested, documented — the kind of OSS I wish more tools were.
> github.com/AI-product-hao/globe-lens-mcp

### Reddit — r/selfhosted or r/dotnet / r/SideProject

> **Show HN-style:** I built GlobeLens, an MCP server that lets AI agents audit
> websites for SEO and internationalization problems (missing `hreflang`/`x-default`,
> accidental `noindex`, mixed content, broken `alt` text, etc.).
>
> It plugs into Claude / Codex / Cursor / Cline and runs a full audit with one tool
> call. The analyzer is pure HTML parsing (no network needed for logic) and every
> change ships with tests. Looking for feedback from anyone shipping multilingual
> sites.
>
> Repo: https://github.com/AI-product-hao/globe-lens-mcp

### 即刻 (Jike) — 中文草稿

> 做了个给 AI 编程助手用的网站 SEO / 国际化审计 MCP 工具 GlobeLens 🌍
> 一句话让 agent 审计任意公网站点：hreflang、lang、canonical、noindex、
> JSON-LD、混合内容、图片 alt 覆盖……一次工具调用出 0–100 分 + 按严重度
> 排序的整改清单。MIT 开源，零配置。出海做站的同学可以试试：
> github.com/AI-product-hao/globe-lens-mcp
> #独立开发 #出海 #SEO #MCP

---

## 7. Next steps (post-streak)

1. **Push** the repo to GitHub (`AI-product-hao/globe-lens-mcp`) and enable the
   existing CI workflow.
2. **Distribute** using the drafts above (X ×2, Reddit, 即刻) — stars follow
   distribution, not just good code.
3. **Extend** (good Codex tasks): sitemap/robots parsing, broader schema.org
   coverage, locale-consistency checks across `hreflang` targets.
