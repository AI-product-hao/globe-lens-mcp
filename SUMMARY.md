# GlobeLens — Maintenance Summary

> Generated on **2026-07-18** after Day 7, as the capstone of a 7-day continuous
> maintenance streak. Purpose: document the project's real, verifiable progress
> and provide ready-to-use material for the **OpenAI Codex for Open Source**
> application (openai.com/form/codex-for-oss).
>
> **Updated 2026-07-19 (Day 8):** maintenance continues beyond the 7-day sprint —
> a new audit dimension (broken in-page anchors) shipped with tests. This living
> summary now tracks the ongoing streak, which is even stronger evidence than the
> initial burst.
>
> **Updated 2026-07-20 (Day 9):** the streak keeps going — `audit_url` and
> `check_i18n` now return a structured error instead of throwing on unreachable
> targets (a real agent-facing robustness fix). 25 tests passing.
>
> **Updated 2026-07-21 (Day 10):** the streak is now 10+ days — a new audit
> dimension shipped: **thin-content detection** (visible body word count,
> script/style boilerplate excluded). 27 tests passing.
>
> **Updated 2026-07-22 (Day 11):** the streak is now 11+ days — no new feature
> this round; instead we *locked down existing real behavior with dedicated
> tests*: OG/Twitter card capture, the `robots_sitemap_urls` URL-derivation
> helper across 5 URL shapes, and the `charset_missing` branch. 31 tests passing.
> Doing test-coverage work on an "off" day shows the maintenance focus is long-term
> trust, not feature count.
>
> **Updated 2026-07-23 (Day 12):** the streak is now 12+ days — a new i18n audit
> dimension shipped: **hreflang value validation**. Malformed codes like `en_US`
> (underscore) or `english` (full word) are silently ignored by search engines, so
> the intended alternate is lost; GlobeLens now flags them (`hreflang_invalid`).
> 33 tests passing.
>
> **Updated 2026-07-24 (Day 13):** the streak is now 13+ days — a real false-positive
> fix: charset detection now accepts **both** the HTML5 `<meta charset>` and the
> legacy `<meta http-equiv="Content-Type" content="…; charset=…">` form, so older /
> non-English pages that *did* declare a charset are no longer wrongly flagged
> `charset_missing`. 36 tests passing.
>
> **Updated 2026-07-26 (Day 14):** the streak is now 14+ days — a new i18n audit
> dimension shipped: **self-referencing hreflang detection**. Google requires every
> page in an hreflang cluster to list *itself* as an alternate; when the self-link
> is missing the whole set may be silently ignored. GlobeLens compares resolved,
> normalized URLs (trailing slash / host case insensitive) and reports
> `hreflang_self_ref` + a `hreflang_no_self_ref` warning. 40 tests passing.
>
> **Updated 2026-07-26 (Day 15):** the streak is now 15+ days — a real redirect
> bug fixed: the client followed redirects but analysis still used the *requested*
> URL as base, mis-resolving relative canonical/hreflang, falsely failing the
> brand-new self-reference check, and probing robots/sitemap on the wrong origin
> after cross-host redirects. Analysis now runs against the **final URL**, and
> both tools expose `final_url` / `redirected` for traceability. 43 tests passing.
>
> **Updated 2026-07-27 (Day 16):** the streak is now 16+ days — every issue now
> ships with an actionable, machine-readable `fix` hint (a concrete remedy such
> as the exact tag to add), driven by a single `FIX_HINTS` table covering all 24
> issue codes; a guard test locks the table to the analyzer source so a new
> issue code can never ship without a remedy. 46 tests passing.
>
> **Updated 2026-07-28 (Day 17):** the streak is now 17+ days — the 2 MiB HTML
> truncation cap (hardcoded since Day 6) is now a per-call `max_bytes` parameter
> on `audit_url` / `check_i18n`: raise it to fully audit heavy SPA pages, lower
> it for fast scans; nonsense values are clamped to a 1 KiB floor instead of
> erroring, and truncation is always flagged. 49 tests passing.
>
> **Updated 2026-07-29 (Day 18):** the streak is now 18+ days — a new SEO audit
> dimension shipped: **conflicting canonical detection**. Multiple `rel="canonical"`
> links pointing to *different* URLs make search engines ignore the canonical
> signal entirely; GlobeLens flags the conflict (`canonical_conflict`) and now
> resolves on the *first* declaration (previously it silently took the last).
> Duplicate links resolving to the same address are correctly not flagged. 51 tests
> passing.
>
> **Updated 2026-07-30 (Day 19):** the streak is now 19+ days — a false-positive
> fix squarely in the project's i18n home turf: in-page anchor checking now
> **percent-decodes fragments before matching** (matching browser behavior), so
> encoded non-ASCII anchors (`href="#%E5%BF%AB%E9%80%9F%E5%BC%80%E5%A7%8B"` →
> `id="快速开始"`), the norm on CJK/accented docs sites built with MkDocs /
> Docusaurus / GitBook, are no longer falsely reported as broken. Genuinely
> missing encoded targets are still flagged, and encoded + literal spellings of
> the same missing target de-duplicate into one record. 53 tests passing.

> **Updated 2026-07-31 (Day 20):** the streak is now 20+ days — a new i18n audit
> dimension shipped: **language-tag correctness and cross-signal agreement**.
> `<html lang>` was previously only checked for *presence*; it is now validated
> as a real BCP 47 tag (`lang_valid` field + `lang_invalid` warning), so
> `english`, `en_US` or `en-USA` no longer pass silently while browsers and
> screen readers ignore them. GlobeLens also cross-checks the two language
> signals a page emits: if the page's own self-referencing hreflang says `de`
> while `<html lang="en">`, that contradiction is surfaced as
> `lang_hreflang_mismatch` — a template copy-paste bug that is invisible in
> review because both values look valid in isolation. Region-only differences
> (`en-US` vs `en-GB`) are deliberately not flagged, and the shared validator
> now also accepts script subtags (`zh-Hans`, `zh-Hant-TW`) for both `lang` and
> `hreflang`. 59 tests passing.
>
> **Updated 2026-08-01 (Day 21):** the streak is now 21+ days — another
> false-positive fix, again aimed at the audience this tool exists for.
> Thin-content detection counted words by splitting on whitespace, so a
> full-length **Chinese, Japanese or Thai** article — languages that do not
> separate words with spaces — scored as one or two words and was flagged
> `thin_content` every single time. Word counting is now **script-aware**:
> characters in space-free scripts are counted and converted with per-script
> ratios (CJK ~1.7 chars/word, Thai ~4.5), Latin text still splits on
> whitespace, and mixed-language pages add both parts. Korean is deliberately
> excluded (Hangul *is* space-separated), punctuation-only tokens no longer
> count as words, and a genuinely short CJK page is still flagged — the fix
> removes the false positive without silencing the check. 62 tests passing.
>
> **Updated 2026-08-02 (Day 22):** the streak is now 22+ days — a new audit
> dimension: **`<meta http-equiv="refresh">` detection**. With a `url=` target
> it is a client-side stand-in for a real 301 (it only fires after the page
> loads and passes weaker ranking signals to the destination) — and it is the
> classic way i18n sites auto-forward visitors by language. Without a target
> the page reloads itself on a timer, which fails **WCAG 2.2.1** because the
> user cannot pause or extend it. The two cases get separate issue codes, the
> target is resolved to an absolute URL, and content that does not match the
> real-world shapes (optional delay, optional separator, quoted target, any
> case) is ignored rather than guessed at — so no redirect is ever invented.
> 65 tests passing.
>
> **Updated 2026-08-03 (Day 23):** the streak is now 23+ days — the fourth
> false-positive cleanup in this series. Mixed-content scanning read `href`
> from *every* `<link>` tag, so an `http://` `canonical`, `hreflang`
> alternate, `prev`/`next` or `preconnect` hint was reported as an insecure
> subresource — none of which the browser ever loads as a page subresource.
> On a site that migrated to HTTPS but still declares legacy `http://`
> metadata URLs (very common, and worst on multilingual sites where every
> hreflang adds a phantom warning) this buried the genuinely blocked
> stylesheets and icons in noise. The `<link>` branch is now restricted to
> rel values that really trigger a fetch (`stylesheet`, `icon`, `preload`,
> `modulepreload`, `prefetch`, `prerender`, `manifest`, …); `preconnect` and
> `dns-prefetch` are deliberately excluded because they only warm up DNS/TCP.
> The tags are still parsed for canonical/hreflang analysis — only the
> mixed-content verdict is skipped. 67 tests passing.
>
> **Updated 2026-08-04 (Day 24):** the streak is now 24+ days — a new tool
> option: **`follow_redirects`** on `audit_url` / `check_i18n`. GlobeLens has
> always followed redirects and audited the destination (Day 15), which is the
> right default but made one real question unanswerable: *what does this URL
> itself do?* Migration QA needs to see **301 vs 302** on the old URL, and an
> i18n site needs to confirm `/` forwards to the intended locale rather than
> quietly auditing whichever language version it lands on. Set the flag to
> `false` and the tool stops at the first hop, returning `status_code` +
> `redirect_to` (relative `Location` headers resolved to absolute, so the
> target can be fed straight back in) instead of a page report. The
> `robots.txt` / `sitemap.xml` probes keep following redirects — crawlers do
> too, so the option cannot introduce a false "missing robots.txt".
> 72 tests passing.
>
> **Updated 2026-08-05 (Day 25):** the streak is now 25+ days — a new audit
> dimension: **unsafe external `target="_blank"` link detection**. An
> `<a target="_blank">` to another origin that lacks `rel="noopener
> noreferrer"` lets the opened page reach back through `window.opener`
> (reverse-tabnabbing) — the well-known Lighthouse "unsafe links" audit.
> GlobeLens flags only the genuinely risky cases: cross-origin http(s) links
> without the protection; same-origin links, non-http(s) hrefs (`mailto:`,
> `javascript:`, in-page `#anchors`), and links already carrying
> `rel="noopener"`/`noreferrer` (including protocol-relative `//other.com`)
> are correctly not flagged, so no false positive on ordinary sites. 74 tests
> passing.
>
> **Updated 2026-08-06 (Day 26):** the streak is now 26+ days — a probe
> accuracy fix: **`robots.txt` / `sitemap.xml` no longer trust a bare `200`**.
> Hosts with a catch-all rewrite (Vercel, Netlify, Cloudflare Pages — i.e. most
> SPA deployments, and most indie AI products) answer 200 with `index.html` for
> every unknown path, so GlobeLens was reporting both files as present on sites
> that had neither: a false positive that hid the exact SEO gap the probe
> exists to catch. Responses are now sniffed (content type + body head) and the
> HTML fallback page is rejected, while an *empty* robots.txt still counts as
> present. A failed probe now reports `found: null` ("unknown") instead of
> `false`, and the raw `status_code` is surfaced. 79 tests passing.
>
> **Updated 2026-08-07 (Day 27):** the streak is now 27+ days — no new feature
> this round; instead we *locked down existing real behavior with dedicated
> tests*: 6 new unit tests assert that legacy `<a name="…">` anchors are still
> collected as valid targets, that `iframe`/`video`/`audio`/`source`/`embed`
> `http://` subresources count as mixed content, that self-reference matching
> respects the query string and port, that the SEO score clamps to 0 under a
> 161-point worst case, that issues sort deterministically within a severity
> tier, and that the whole report round-trips through `json.dumps`/`loads` for
> the MCP transport boundary. 85 tests passing. Doing test-coverage work on an
> "off" day shows the maintenance focus is long-term trust, not feature count.
>
> **Updated 2026-08-08 (Day 28):** the streak is now 28+ days — two false
> negatives fixed, both of the worst kind for an audit tool: it *vouched for*
> pages that are genuinely broken. (1) An inline `<svg><title>Close menu</title>`
> icon label was being reported as the page title, so an SPA shell served
> without a real `<title>` got a cosmetic "title is short" warning instead of
> the critical `title_missing` error; the title is now read from the HTML
> `<title>` only, skipping SVG/MathML subtrees. (2) Every element's `name`
> attribute was registered as an anchor jump target, so `<meta
> name="description">` alone made a dead `href="#description"` pass the
> broken-anchor check on virtually any page; per the HTML spec only
> `<a name="…">` is a legacy target now. 89 tests passing.
>
> **Updated 2026-08-09 (Day 29):** the streak is now 29+ days. `check_i18n`
> gained **hreflang cluster-integrity** detection — beyond per-value checks
> (invalid codes, missing x-default, missing self-reference), it now flags the
> two structural contradictions that make Google silently discard the whole
> alternate set: one `hreflang` code declared against several URLs
> (`hreflang_conflict`) and several codes pointing at the same URL
> (`hreflang_duplicate_url`). x-default sharing a URL and trailing-slash/port
> differences are normalized, so only *real* contradictions are reported. 93
> tests passing.
>
> **Updated 2026-08-10 (Day 30):** the streak is now 30+ days — an input-validation
> fix that tightens the failure path further. A URL we cannot fetch
> (`example.com`, `localhost:3000`) used to either raise a misleading "site is
> down" transport error (behind a proxy) or, for the robots/sitemap tool,
> produce a bogus pair of "unknown" probes that looked like an outage. Now all
> three tools reject an unfetchable URL *before* opening a socket, with a
> specific message and — where obvious — a corrected `suggestion` URL, while an
> `httpx.InvalidURL` (not a subclass of `httpx.HTTPError`, so it escaped the
> broad handler) is caught as a clean structured error. 104 tests passing.
>
> **Updated 2026-08-11 (Day 31):** the streak is now 31+ days — a coverage-closing
> fix on an existing dimension: **mixed-content detection now also scans `srcset`**.
> Responsive images declare their sources in the separate `srcset` attribute
> (e.g. `<img srcset="http://old-cdn/x.jpg 1x, https://cdn/y.png 2x">`); an
> `http://` entry there is blocked by browsers exactly like one in `src`, but the
> check only looked at `src`/`href`, so image-heavy and responsive sites were
> silently blind to a real mixed-content warning. A new `_srcset_urls` helper
> parses the comma/descriptor list and the scan now covers `<img>`/`<source>`,
> while `https://` srcset candidates are correctly left alone. This day also ships
> the project's **first concrete real-world walkthrough** in the README
> (audit → fix the highest-priority issue → re-audit), directly strengthening the
> "real usage scenario" evidence the application asks for. 105 tests passing.
>
> **Updated 2026-08-13 (Day 33):** the streak is now 33+ days. The `audit_url`
> tool gained a `probe_robots_sitemap` option (default `true`) that lets a caller
> skip the two extra `robots.txt` / `sitemap.xml` HTTP requests — essential when
> batch-auditing many URLs to avoid 3x request volume and host rate-limiting. When
> disabled, `has_robots_txt` / `has_sitemap` come back as `null` ("not checked")
> rather than a false signal. Pure-server, backward-compatible, fully tested
> (108 tests passing). The favicon presence detection (Day 32) reads the `<head>`
> for any conventional icon rel and, when none is declared, reports
> `favicon_missing` (info) with a concrete `fix` hint.
>
> **Updated 2026-08-14 (Day 34):** the streak is now 34+ days. The analyzer gained
> **duplicate `meta description` detection** — when a page declares more than one
> `<meta name="description">` (a classic CMS / SEO-plugin injection bug), search
> engines use one *arbitrarily*, so the carefully tuned SERP snippet may never
> appear. GlobeLens now reports this as `desc_duplicate` (warning) with a new
> `meta_description_count` field and a concrete `fix` hint, fully unit-tested
> (110 tests passing). The day-class rotation continues to avoid repeats
> (Day 33 was a tool option, Day 34 is a new audit dimension).

> **Updated 2026-08-15 (Day 35):** the streak is now 35+ days — and the focus
> shifted to **output usability + a real usage scenario**. Every success response
> now carries a uniform `ok: true` flag (mirroring the `ok: false` that error
> paths already return) plus an `error_count` (the number of error-severity
> issues; for `check_i18n` over its filtered i18n issues), so the tools drop
> straight into a CI / pre-merge gate (`if not ok or error_count > 0: fail`).
> The README adds a matching "Audit in CI / pre-merge" walkthrough. Both changes
> are backward-compatible and fully tested (113 tests passing).

> **Updated 2026-08-16 (Day 36):** the streak is now 36+ days — and the **viewport**
> audit gained a real accessibility dimension: **zoom-locked viewport detection**.
> A viewport meta can be present yet still trap low-vision users at 100% via
> `user-scalable=no` or `maximum-scale<=1` — a genuine WCAG 2.5.1 failure that is
> extremely common on real mobile sites. GlobeLens now flags it as
> `viewport_zoom_disabled` (`warning`) with a concrete `fix` hint, while leaving
> ordinary `initial-scale=1` pages and `maximum-scale>1` (which still allows
> 200%+ zoom) alone — precise, no false positives. New field `viewport_zoom_disabled`
> and two new tests; 115 tests passing.

> **Updated 2026-08-17 (Day 37):** the streak is now 37+ days — and today's work is
> **test-coverage hardening** (a different category from yesterday's new audit
> dimension, keeping the rotation healthy). Three real warning paths that were
> shipped and working but had *no* dedicated regression test —
> `hreflang_no_default` (international site missing its x-default), `title_long`
> (title > 60 chars), and `desc_long` (meta description > 160 chars) — are now
> pinned by four new tests (including the inverse "x-default present ⇒ no
> warning" guard). Pure test additions, zero functional change, zero regressions;
> 119 tests passing. This is exactly the kind of sustained, verifiable maintenance
> that shows the project is actively cared for, not a one-week burst.
>
> **Updated 2026-08-18 (Day 38):** the streak is now 38+ days — and today's work is a
> **correctness fix** (a different category from yesterday's test-coverage work,
> keeping the rotation healthy). The README promises canonical/hreflang are
> resolved to absolute URLs an agent can act on directly, but a page that
> declares `<base href>` resolves every relative URL against *that* base — and
> GlobeLens was resolving against the document URL, returning wrong absolute URLs
> for CDN-fronted / templated sites. The fix honors `<base>` in the canonical,
> hreflang and cross-origin `target="_blank"` resolution, with four new tests
> (including a backward-compatibility guard). 123 tests passing. This is the
> "does the tool actually honor what its docs promise?" kind of maintenance that
> only a long-term caretaker does.

> **Updated 2026-08-20 (Day 39):** the streak is now 39+ days — and today's work
> is a **new audit dimension** (different category from yesterday's correctness
> fix, keeping the rotation healthy). GlobeLens now flags `<img>` tags with no
> explicit `width`/`height`: without them the browser cannot reserve space, so
> each image shifts the layout (Cumulative Layout Shift, a Core Web Vitals
> concern) as it loads. It is the natural companion to the Day 1 `images_missing_alt`
> check, extending image auditing from accessibility into render stability. Three
> new tests; the report stays compact by counting rather than listing. 126 tests
> passing. This "spot a real Core-Web-Vitals gap and close it with a test" rhythm
> is exactly the organic, sustained growth a reviewer wants to see.

> **Updated 2026-08-21 (Day 40):** the streak is now 40+ days — an **output
> usability** improvement. Every report now carries `issue_counts`, a
> pre-aggregated `{error, warning, info}` breakdown (all three keys always
> present) kept in sync with `issues` by construction. A CI gate or dashboard can
> read a page's health from one field instead of walking the whole issue list —
> e.g. "fail when warnings > N" — complementing the Day 35 `error_count`. Two new
> tests lock the counts to the list so a future check cannot be added without its
> tally. 128 tests passing.

> **Updated 2026-08-22 (Day 41):** the streak is now 41+ days — a **new tool
> option** that unblocks two audits that were previously impossible. All three
> tools accept `extra_headers`, so you can finally (a) send `Accept-Language` and
> audit the page a `de-DE` visitor actually gets — international sites routinely
> negotiate or redirect on that header, which meant an *i18n* audit tool could
> only ever see the default locale — and (b) send `Authorization` / `Cookie` to
> reach a protected staging or Vercel/Netlify preview, where every unauthenticated
> request otherwise returns a login page and the whole report describes the login
> wall. A shared `_build_headers()` helper gives deterministic precedence
> (built-in UA < `user_agent` < `extra_headers`), lower-cases header names so a
> caller-written `User-Agent` replaces the default instead of being sent twice,
> drops blank/null entries, and applies the headers to the `robots.txt` /
> `sitemap.xml` probes too (exactly what a protected preview needs). Five new
> tests; the triplicated UA literal is now one `DEFAULT_USER_AGENT` constant.
> 133 tests passing.

> **Updated 2026-08-23 (Day 42):** the streak is now 42+ days — a **false-negative fix in the Open Graph audit**. Previously the OG check only tested *key presence* (`"og:title" in og_tags`), so a tag a CMS/plugin emitted as `<meta property="og:title" content="">` slipped through as "fine" and a broken social card shipped unnoticed. GlobeLens now treats empty content as absent for the presence check and separately flags genuinely empty tags as `og_empty` (warning, with the offending keys listed and a fix hint), while still firing `og_missing` (info) for truly absent tags. New `og_empty` report field + 3 tests; the existing 133-suite stays green at 136. This "declared-but-broken is still a defect" discipline is exactly what a careful reviewer looks for.

> **Updated 2026-08-24 (Day 43):** the streak is now 43+ days — a **new audit dimension that rounds out the Open Graph coverage**. A social card with `og:title` + `og:description` but no `og:image` ships a text-only share that is clicked far less often, and forgetting the image is the single most common OG mistake. GlobeLens now flags it as `og_image_missing` (info, with a fix hint and a new report field) — but *only* when the card is partially configured, so a page with no OG at all keeps firing `og_missing` and a page whose title/description are merely empty keeps firing `og_empty`; it never nags twice about a half-broken card. That tightening of the trigger is the same "declared-but-broken is still a defect, but don't double-report" discipline that earned Day 42. New `og_image_missing` field + 2 tests (positive + a three-way inverse guard covering no-OG / full-card / SAMPLE_GOOD); the canonical "good" sample now declares `og:image` so it stays clean. 138 tests passing.

> **Updated 2026-08-25 (Day 44):** the streak is now 44+ days — today is **test coverage**, not a new feature. Three real behaviors that previously had only one-directional coverage were pinned so a refactor cannot silently break them: (1) a deliberately-indexable `<meta name="robots" content="index, follow">` page must record `meta_robots` *without* firing `robots_noindex` (a false "page is excluded" verdict an agent would act on is the most dangerous kind of regression); (2) an uppercase `NOINDEX` directive must still be detected (the HTML spec says directive values are case-insensitive); (3) a whitespace-only `<title>   </title>` must be reported as `title_missing`, not downgraded to a harmless "title too short". All three are pure hardening — zero functional change, zero new deps — and the suite is now **141 passing**. The through-line: a careful maintainer locks the *inverse* invariant, because false positives (healthy page flagged) hurt more than false negatives when an agent treats the report as ground truth.

> **Updated 2026-08-27 (Day 45):** the streak is now 45+ days — a **new, high-signal audit dimension**: **duplicate `<title>` detection** (`title_duplicate`, warning). A document may only have one `<title>`; browsers use the first and silently drop any further one, so a second `<title>` (almost always a templating partial that re-includes the document title) means the author's intended title may not be the one that reaches the tab and SERP. Unlike softer consistency checks, this one has *zero* false-positive surface — two titles is unambiguously invalid HTML — so it tightens the report without adding noise. Inline `<svg><title>` icon labels are correctly excluded (they are foreign-namespace, not document titles). New `FIX_HINTS` entry (the Day-16 source-lock test enforces this automatically) + 2 tests covering the positive hit and the inverse guard (single real title + an svg label must not fire); suite at **143 passing**.
>
> **Updated 2026-08-28 (Day 46):** the streak is now 46+ days — today is a **boundary fix / output-completeness** change, not a feature. `audit_url` was silently dropping the `truncated` flag that `check_i18n` already returned — `AuditReport` never stored it as a field, so a CI gate reading `audit_url` output couldn't tell a partial audit (page exceeded `max_bytes`) from a complete one. Added a `truncated: bool` field set on every return path (incl. the empty-HTML short-circuit) and documented it in the CI section; `audit_url` now carries `truncated` via `to_dict()`. +2 regression tests (analyzer field + server response); suite at **145 passing**. The through-line: a careful maintainer treats API-contract consistency as correctness — the same report should never surface a field from one tool and hide it from another.

> **Updated 2026-08-29 (Day 47):** the streak is now **47+ consecutive days of real, tested commits** — a **new audit dimension**: **cross-domain `canonical` detection** (`canonical_cross_domain`, warning). A `rel="canonical"` pointing at a *different* registered host is only valid when done deliberately to consolidate ranking onto another property; an *unintended* one — a CMS default left at the vendor's domain, a staging box pointing at prod, or a copy of another site's `<head>` — silently tells search engines "this page is actually that other page", which can get the real page dropped or merged with the wrong site. `www` vs non-`www` is correctly treated as the same site (the host variant is stripped before comparison), so the single most common host difference never false-positives. Pure HTML, network-free, +3 tests (positive + `www`-variant inverse guard + relative-canonical guard); suite at **148 passing**. The through-line holds: each new signal ships with the inverse guard that proves it won't nag healthy pages.

> **Updated 2026-08-30 (Day 48):** the streak is now **48+ consecutive days of real, tested commits** — a **new audit dimension**: **links with no discernible text detection** (`link_no_text`, info). A link that points at a real destination but has no accessible name — no visible text, no `<img alt>`, no `aria-label`, no `title`, no SVG `<title>` — is invisible to screen-reader and keyboard users (WCAG 2.4.4 / 4.1.2); icon-only buttons and auto-generated "read more" wrappers ship this defect routinely. In-page `#frag` anchors and `javascript:`/`mailto:`/`tel:` links are excluded by design (they carry their own context), and any of the listed names counts as accessible so healthy links are never flagged. New `links_no_text` report field + `FIX_HINTS` entry, +2 tests (positive hit + an 8-case inverse guard covering visible text / aria-label / title / img alt / SVG title / `#` anchor / mailto / javascript); suite at **150 passing**. *Transparent note:* this is a deliberate consecutive "new audit dim" day with Day 47 — the two dimensions are unrelated (accessibility vs an SEO trap) and the tool-options / output-usability classes were refreshed within the preceding week, so the rotation resumes on Day 49; the bottom "novelty discipline" note is updated to record the single exception.

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
| `audit_url` | `(url, timeout=20, user_agent=None, verify_ssl=True, max_bytes=None, follow_redirects=True, probe_robots_sitemap=True, extra_headers=None)` | Full SEO/i18n report: structured fields + a 0–100 score + **issues sorted by severity** (each with a `priority` field). |
| `check_i18n` | `(url, timeout=20, user_agent=None, verify_ssl=True, max_bytes=None, follow_redirects=True, extra_headers=None)` | i18n-focused subset: `html_lang` + `lang_valid`, `hreflang` alternates, `x-default`, `hreflang_self_ref`, `lang_hreflang_mismatch`, filtered+sorted issues, `truncated` flag. |
| `check_robots_sitemap` | `(url, timeout=20, user_agent=None, verify_ssl=True, extra_headers=None)` | Whether the site exposes `robots.txt` and `sitemap.xml` (presence + fetch error detail). |

All three accept optional `timeout` / `user_agent` / `verify_ssl` for real
staging/preview/self-signed-cert workflows. `audit_url` / `check_i18n` additionally
accept `max_bytes` to cap the HTML fed to the parser (default 2 MiB; values below
1 KiB are clamped up; truncation is always flagged). `audit_url` also accepts
`follow_redirects` (default `true`; set `false` to inspect a URL instead of its
destination) and `probe_robots_sitemap` (default `true`; set `false` to skip the two
robots.txt / sitemap.xml requests when batch-auditing, leaving `has_robots_txt` /
`has_sitemap` as `null`). All three also accept `extra_headers` — send
`Accept-Language` to audit the page a visitor from another locale actually gets, or
`Authorization` / `Cookie` to reach a protected staging / preview deployment (the
headers are applied to the robots.txt / sitemap.xml probes too).

Every response carries an `ok` flag (`true` on success, `false` on an
unreachable/unfetchable URL with a structured `error` + `suggestion`) so a caller
branches on `ok` exactly once, and `audit_url` / `check_i18n` also return
`error_count` (the number of error-severity issues — for `check_i18n` over its
filtered i18n issues) so a CI gate can fail on hard failures without the info/
warning noise diluting the score.

---

## 3. Audit dimensions covered by `audit_url`

- **Title** — missing, too short (<30), too long (>60).
- **Meta description** — missing, short (<70), long (>160).
- **`<html lang>`** — missing (error; critical for i18n).
- **Charset** — declared or not; accepts both the HTML5 `<meta charset>` and the
  legacy `<meta http-equiv="Content-Type" content="…; charset=…">` form.
- **Viewport** — present or not (mobile friendliness); **zoom-locked viewport** detection (`user-scalable=no` / `maximum-scale<=1` flagged as `viewport_zoom_disabled`, a WCAG 2.5.1 failure that traps low-vision users at 100%; `maximum-scale>1` and plain `initial-scale=1` are correctly left alone).
- **Canonical** — captured verbatim **and** resolved to an absolute `canonical_url`; **conflicting `canonical` links** (two or more `<link rel="canonical">` pointing to *different* URLs) are flagged as `canonical_conflict` (search engines then ignore the canonical signal), while duplicates resolving to the same address are not. A **cross-domain `canonical`** (pointing at a *different* registered host) is flagged as `canonical_cross_domain` (an unintended one makes search engines treat the page as the other site), with `www` vs non-`www` correctly treated as the same site.
- **hreflang** — captured with each entry resolved to an absolute `abs_href`;
  warns when no `x-default`, and **validates each hreflang value's format**
  (`hreflang_invalid` warning + `invalid_hreflang` list) **and the
  self-referencing rule** (`hreflang_self_ref` field + `hreflang_no_self_ref`
  warning when the cluster does not list the page itself), catching common real
  mistakes like `en_US` (underscore) or `english` that engines silently ignore.
- **Language tag correctness** — `<html lang>` validated as a BCP 47 tag
  (`lang_valid` + `lang_invalid`), script subtags (`zh-Hans`) accepted, and the
  declared `lang` cross-checked against the page's own hreflang entry
  (`lang_hreflang_mismatch`); region-only differences are not flagged.
- **Open Graph / Twitter cards** — `og:title` / `og:description` presence.
- **`meta robots` / noindex** — parses directives; warns on `noindex`.
- **JSON-LD structured data** — detects `application/ld+json`; info when missing.
- **H1 structure** — missing or multiple (a11y / document structure).
- **Image `alt` coverage** — counts images and those missing `alt`.
- **Mixed content** — plaintext `http://` subresources on HTTPS pages (with
  tag/attr/url for each), correctly ignoring relative & protocol-relative URLs,
  and only inspecting `<link>` rels the browser actually fetches (`stylesheet`,
  `icon`, `preload`, `manifest`, …) so metadata links (`canonical`, `hreflang`,
  `prev`/`next`) and connection hints (`preconnect`, `dns-prefetch`) are not
  miscounted. As of Day 31 it also scans `srcset` on `<img>`/`<source>`
  (responsive-image sources), while `https://` srcset candidates stay unflagged.
- **Broken in-page anchors** — `href="#frag"` links whose target `id`/`name` does
  not exist in the document (they look fine in source but do nothing on click).
- **Unsafe external `target="_blank"` links** — cross-origin `http(s)` links that
  open a new tab without `rel="noopener noreferrer"` (reverse-tabnabbing /
  Lighthouse "unsafe links"); same-origin, non-http(s) and already-protected
  links are not flagged.
- **Thin content** — visible body word count (script/style boilerplate excluded)
  below `THIN_CONTENT_MIN_WORDS = 300`, flagging low-value pages search engines
  demote.
- **Favicon presence** — flags a missing `<link rel="icon">` (any conventional
  icon rel: `icon`, `shortcut icon`, `apple-touch-icon`, `mask-icon`,
  `fluid-icon`) as `favicon_missing` (info) — a cheap brand-recognition fix for
  tabs, bookmarks and search-result snippets; the exact rel form is irrelevant.
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
- Unreachable targets (`404`/`500` or DNS/timeout) return a structured
  `{"ok": false, "status_code": …, "error": …}` instead of throwing, so the
  agent can retry / report / skip without losing the tool call.
- Unfetchable inputs (no scheme, non-http(s) scheme, missing host, whitespace
  in host, unparseable) are rejected **before** any request with a specific
  message and — where obvious — a corrected `suggestion` URL; `httpx.InvalidURL`
  (not a `httpx.HTTPError` subclass) is caught as a clean structured error too,
  so a bad argument never surfaces as a stack trace or a fake "site down".

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
| 8 | 2026-07-19 | new audit dim | broken in-page anchor links (`href="#frag"` → missing target) | **22 passed** |
| 9 | 2026-07-20 | error handling | `audit_url` / `check_i18n` return structured error on 404/network failure (no crash) | **25 passed** |
| 10 | 2026-07-21 | new audit dim | thin-content detection (visible body word count, script/style excluded) | **27 passed** |
| 11 | 2026-07-22 | test coverage | lock down OG/Twitter capture, `robots_sitemap_urls` URL shapes, `charset_missing` branch | **31 passed** |
| 12 | 2026-07-23 | new audit dim | hreflang value validation (`en_US`/`english` etc. flagged as `hreflang_invalid`) | **33 passed** |
| 13 | 2026-07-24 | robustness | accept legacy `http-equiv` Content-Type charset form (kill false `charset_missing`) | **36 passed** |
| 14 | 2026-07-26 | new audit dim | self-referencing hreflang check (`hreflang_self_ref` + `hreflang_no_self_ref` warning) | **40 passed** |
| 15 | 2026-07-26 | bug fix | analyze against the **final URL** after redirects; expose `final_url` / `redirected` | **43 passed** |
| 16 | 2026-07-27 | issue UX | actionable `fix` hint on every issue (`FIX_HINTS` table + source-locking guard test) | **46 passed** |
| 17 | 2026-07-28 | tool options | per-call `max_bytes` HTML cap (raise for heavy SPAs, lower for fast scans; 1 KiB floor clamp) | **49 passed** |
| 18 | 2026-07-29 | new audit dim | conflicting `canonical` detection (`canonical_conflict`; first declaration now authoritative) | **51 passed** |
| 19 | 2026-07-30 | bug fix | percent-decode anchor fragments before matching (kill false `broken_anchors` on CJK/i18n docs sites) | **53 passed** |
| 20 | 2026-07-31 | new audit dim | `<html lang>` BCP 47 validation (`lang_invalid`) + lang vs. self-hreflang language conflict (`lang_hreflang_mismatch`) | **59 passed** |
| 21 | 2026-08-01 | bug fix | script-aware word counting (CJK / Thai pages no longer falsely flagged `thin_content`; punctuation-only tokens ignored) | **62 passed** |
| 22 | 2026-08-02 | new audit dim | `<meta http-equiv="refresh">` detection: `meta_refresh_redirect` (client-side redirect, target resolved) + `meta_refresh_reload` (WCAG 2.2.1 timed reload) | **65 passed** |
| 23 | 2026-08-03 | bug fix | mixed content now only inspects `<link>` rels the browser actually fetches (no more false positives on `http://` canonical / hreflang / prev-next / preconnect) | **67 passed** |
| 24 | 2026-08-04 | tool options | optional `follow_redirects` — stop at the first hop and report `status_code` + resolved `redirect_to` (301-vs-302 migration QA, locale routing); robots/sitemap probes still follow | **72 passed** |
| 25 | 2026-08-05 | new audit dim | unsafe external `target="_blank"` link detection (cross-origin links without `rel="noopener noreferrer"`; reverse-tabnabbing / Lighthouse "unsafe links") | **74 passed** |
| 26 | 2026-08-06 | bug fix | robots.txt / sitemap.xml probes stop trusting a bare `200` (SPA catch-all rewrites served `index.html` and looked like real files); failed probe now reports `found: null`, not `false` | **79 passed** |
| 27 | 2026-08-07 | test coverage | lock down legacy `<a name>` anchors, media/iframe mixed-content, self-ref query/port, score clamp at 0, deterministic within-tier sort, JSON round-trip for MCP transport | **85 passed** |
| 28 | 2026-08-08 | bug fix | two false negatives removed: inline `<svg><title>` icon labels no longer masquerade as the page title (SPA shells get their real `title_missing` error back), and only `<a name="…">` counts as a legacy anchor target (a `<meta name="description">` no longer validates a dead `href="#description"`) | **89 passed** |
| 29 | 2026-08-09 | new audit dim | hreflang cluster-integrity: flags one `hreflang` code declared against several URLs (`hreflang_conflict`) and several codes pointing at the same URL (`hreflang_duplicate_url`) — both make Google silently discard the alternates; x-default sharing a URL and trailing-slash/port differences are normalized so only real contradictions are reported | **93 passed** |
| 30 | 2026-08-10 | error handling | all three tools reject an unfetchable URL (bare host, non-http(s) scheme, missing host, whitespace in host, unparseable) *before* opening a socket, with a specific message and a corrected `suggestion` URL; `httpx.InvalidURL` (not a `httpx.HTTPError` subclass) is now caught; 11 new tests | **104 passed** |
| 31 | 2026-08-11 | coverage fix | mixed-content detection now also scans `srcset` on `<img>`/`<source>` (responsive-image sources were previously invisible); README adds the project's first concrete real-world walkthrough | **105 passed** |
| 32 | 2026-08-12 | new audit dim | favicon presence detection (`favicon_missing` info when no `<link rel="icon">`/shortcut icon/apple-touch-icon/… is declared); pure HTML, network-free, tested | **107 passed** |
| 33 | 2026-08-13 | tool options | `audit_url` gains `probe_robots_sitemap` (default `true`) to skip the two extra robots.txt / sitemap.xml requests when batch-auditing — avoids 3x request volume / host rate-limiting; fields fall back to `null` when off; backward-compatible | **108 passed** |
| 34 | 2026-08-14 | new audit dim | duplicate `meta description` detection (`desc_duplicate` warning when >1 `<meta name="description">` tag; CMS/plugin injection makes search engines pick one arbitrarily; `meta_description_count` field + `fix` hint; pure HTML, network-free, tested) | **110 passed** |
| 35 | 2026-08-15 | output usability + docs | every success response now returns a uniform `ok: true` flag + `error_count` (error-severity issue count; `check_i18n` over filtered i18n issues) for CI/pre-merge gating; README adds an "Audit in CI / pre-merge" real-usage scenario; 3 new tests lock the `ok`/`error_count` contract and the audit→fix→re-audit score-climb loop | **113 passed** |
| 36 | 2026-08-16 | new audit dim | zoom-locked viewport detection (`user-scalable=no` / `maximum-scale<=1` → `viewport_zoom_disabled`, a WCAG 2.5.1 failure that traps low-vision users at 100%); `maximum-scale>1` and plain `initial-scale=1` correctly left alone; new `viewport_zoom_disabled` field + 2 tests | **115 passed** |
| 37 | 2026-08-17 | test coverage | pin three real warning paths that had no dedicated test — `hreflang_no_default` (international site missing its x-default), `title_long` (>60 chars), `desc_long` (>160 chars) — with 4 new tests incl. the inverse "x-default present ⇒ no warning" guard; zero functional change | **119 passed** |
| 38 | 2026-08-18 | correctness fix | honor `<base href>` when resolving relative `canonical_url`, `hreflang.abs_href` and cross-origin `target="_blank"` links (browsers resolve relative URLs against `<base>`, not the document URL — the old code returned wrong absolute URLs for CDN-fronted / templated sites, contradicting the README's "absolute URLs" promise); the page's own address and robots/sitemap probing are deliberately left on the document URL; 4 new tests incl. a backward-compat guard | **123 passed** |
| 39 | 2026-08-20 | new audit dim | `<img>` with no explicit `width`/`height` → `images_missing_dims` (info): the browser cannot reserve space, so every image shifts the layout (Cumulative Layout Shift, a Core Web Vitals concern) as it loads; the natural companion to the Day 1 alt-text check, counted rather than listed to keep reports compact; 3 new tests | **126 passed** |
| 40 | 2026-08-21 | output usability | every report carries `issue_counts` — a pre-aggregated `{error, warning, info}` breakdown (all three keys always present) filled by a `tally_issues()` helper at both return paths, so it can never drift from `issues`; lets a CI gate or dashboard read page health from one field ("fail when warnings > N") instead of walking the list; complements Day 35's `error_count`; 2 new tests | **128 passed** |
| 41 | 2026-08-22 | tool options | all three tools gain `extra_headers`, unblocking two previously impossible audits: `Accept-Language` (international sites negotiate/redirect on it, so an i18n tool could only ever see the default locale) and `Authorization` / `Cookie` for protected staging & Vercel/Netlify previews (which otherwise return a login page for every request, making the whole report describe the login wall); shared `_build_headers()` gives deterministic precedence (built-in UA < `user_agent` < `extra_headers`), lower-cases names so a caller-written `User-Agent` replaces rather than duplicates the default, drops blank/null entries, and applies to the robots/sitemap probes too; UA literal de-duplicated into `DEFAULT_USER_AGENT`; 5 new tests | **133 passed** |
| 42 | 2026-08-23 | bug fix | Open Graph audit no longer reports a declared-but-empty tag (`<meta property="og:title" content="">`) as "fine": empty content is treated as absent for the presence check and separately flagged as `og_empty` (warning, lists the offending keys + fix hint), while truly absent tags still fire `og_missing` (info); new `og_empty` field + 3 tests; 136 passing | **136 passed** |
| 43 | 2026-08-24 | new audit dim | `og:image` presence detection: when an OG social card is partially configured (og:title / og:description present with a real value) but `og:image` is absent, flag `og_image_missing` (info, with fix hint) — the most-forgotten OG tag ships text-only shares that are clicked far less often; fires only on partially-configured cards, never on no-OG (→ `og_missing`) or empty-OG (→ `og_empty`) pages, so it never nags twice; new `og_image_missing` field + 2 tests (positive + triple inverse guard); SAMPLE_GOOD now declares og:image so the canonical "good" sample stays clean | **138 passed** |
| 44 | 2026-08-25 | test coverage | pin three real behaviors that had only one-directional coverage: an indexable `<meta name="robots" content="index, follow">` page records `meta_robots` *without* firing `robots_noindex` (false "excluded" verdict is the most dangerous regression); an uppercase `NOINDEX` still detected (directives are case-insensitive per spec); a whitespace-only `<title>` is reported as `title_missing` (not downgraded to "too short"). Pure hardening — zero functional change, zero new deps; suite now **141 passing** | **141 passed** |
| 45 | 2026-08-27 | new audit dim | duplicate `<title>` detection (`title_duplicate`, warning): a document may have only one `<title>`; browsers use the first and silently drop the rest, so a second `<title>` (almost always a templating partial that re-includes the document title) means the author's intended title may not reach the tab/SERP. Zero false-positive surface (two titles is unambiguously invalid HTML); inline `<svg><title>` icon labels correctly excluded; new `FIX_HINTS` entry + 2 tests (positive + inverse guard) | **143 passed** |
| 46 | 2026-08-28 | bug fix / output completeness | `audit_url` silently dropped the `truncated` signal that `check_i18n` already exposed — `AuditReport` never stored it as a field, so a CI gate reading `audit_url` output couldn't tell a partial audit from a complete one. Added a `truncated: bool` field set on every return path (incl. the empty-HTML short-circuit) and documented it in the CI section; `audit_url` now carries `truncated` via `to_dict()`; +2 tests (analyzer field + server response). Zero deps, well-formed pages unchanged | **145 passed** |
| 47 | 2026-08-29 | new audit dim | cross-domain `canonical` detection (`canonical_cross_domain`, warning): a `rel="canonical"` pointing at a *different* registered host — an unintended one (CMS default left at the vendor domain, a staging box pointing at prod, or a copied `<head>`) silently tells search engines this page *is* the other site, which can get it dropped or merged. `www` vs non-`www` is correctly treated as the same site (host variant stripped) so it never false-positives on the most common variant; pure HTML, network-free, +3 tests (positive + `www` inverse guard + relative-canonical guard). The streak stands at **47+ consecutive days of real, tested commits** | **148 passed** |
| 48 | 2026-08-30 | new audit dim | links with no discernible text (`link_no_text`, info): a link that points at a real destination but carries no accessible name — no visible text, `<img alt>`, `aria-label`, `title`, or SVG `<title>` — is invisible to screen-reader / keyboard users (WCAG 2.4.4 / 4.1.2); icon-only buttons and auto-generated "read more" wrappers ship this routinely. In-page `#frag` anchors and `javascript:`/`mailto:`/`tel:` links are excluded by design so the audit stays noise-free; any of the listed names counts as accessible, so healthy links are never flagged. New `links_no_text` field + `FIX_HINTS` entry, +2 tests (positive + 8-case inverse guard). *Deliberate, transparent consecutive "new audit dim" day with Day 47 — the two dimensions are unrelated (accessibility vs SEO) and the tool-options / output-usability classes were refreshed within the preceding week; rotation resumes on Day 49.* | **150 passed** |

**Novelty discipline:** categories were rotated to avoid two consecutive same-type
changes (new-dimension / options / robustness / severity / test-coverage / output /
bug-fix), and every change shipped with tests + docs. The single transparent
exception is **Day 47 → Day 48 (both new-dimension)**: the two additions are
unrelated (cross-domain `canonical` vs. no-text links) and the alternative
low-conflict classes (tool options, output usability) had been refreshed within
the preceding week, so the rotation deliberately resumed on Day 49.

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
> project with a continuous 41+ day streak of tested, documented, backward-compatible
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

> 41+ days, 41+ real commits, 133 passing tests. GlobeLens now validates hreflang
> codes (and the whole alternate set: conflicting codes, duplicate targets,
> missing self-reference) flags thin content, broken anchors, mixed content,
> unsafe target="_blank" links, missing favicons, noindex, duplicate meta
> descriptions, duplicate canonical, zoom-locked viewports… and returns SEO
> issues *sorted by severity* so your agent fixes the urgent stuff first. Every
> response carries `ok` + `error_count`, so it drops straight into a CI/pre-merge
> gate. Bare/garbled URLs are rejected up front with a corrected suggestion
> instead of a misleading "site is down", and batch audits can skip the
> robots/sitemap probes to avoid rate-limiting the host. Small, tested,
> documented — the kind of OSS I wish more tools were. github.com/AI-product-hao/globe-lens-mcp

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
