# GlobeLens 维护日志（PROGRESS）

> 由每日自动化维护任务更新。目标：连续 7 天真实迭代，建立开源维护轨迹，
> 为 OpenAI **Codex for Open Source** 申请（openai.com/form/codex-for-oss）积累证据：
> 真实活跃 + 真实使用场景。

## Day 0 — 项目初始化（2026-07-12）
- 创建仓库骨架：analyzer.py（SEO/i18n 分析逻辑，无网络依赖、单测友好）、
  server.py（FastMCP 服务，暴露 3 个工具）、tests、README、LICENSE(MIT)、CI。
- 实现工具：`audit_url` / `check_i18n` / `check_robots_sitemap`。
- 本地单测通过（pytest，2 个用例：良好页检测 + 缺失 lang 标记）。
- 待办：推送到 GitHub（AI-product-hao/globe-lens-mcp）、补充分发（X / Reddit / 即刻）。

## Day 1 — 2026-07-12
- **新增审计维度（on-page 结构与可访问性）**：
  - 检测 `<h1>` 结构：缺失（`h1_missing`）或存在多个（`h1_multiple`，warning）。
  - 检测图片 `alt` 文本覆盖：新增 `images_total` / `images_missing_alt` 字段，缺失时给出 `images_missing_alt` warning。
  - 在 `AuditReport` 增加 `h1_count`、`images_total`、`images_missing_alt` 三个字段（向后兼容，均为默认值，不影响既有 `to_dict`）。
- **测试**：新增 2 个用例（`test_flags_onpage_structure_issues`、`test_clean_onpage_structure_has_no_structure_issues`），覆盖多重 H1 + 缺 alt、单 H1 无图无告警两种场景；总用例 2 → 4，全部通过。
- **文档**：README Features 中 `audit_url` 说明补充 H1 结构与图片 alt 覆盖。
- **测试结果**：`pytest -q` → 4 passed。
- **对 Codex for OSS 申请的贡献**：展示「持续往真实可用的审计能力上加法」——这不是空壳项目，而是有清晰 roadmap、每个改动可测试、且紧贴真实 SEO/可访问性痛点（H1 与图片 alt 是站长最常踩的坑）。真实使用场景：AI 编辑器中让 agent 在写页面时即时发现结构/可访问性问题。

## Day 2 — 2026-07-13
- **工具可选参数（与 Day 1 不同类，避免连续同类）**：为全部三个 MCP 工具新增可选参数，让 AI agent 在真实场景下更可控地调用：
  - `timeout`（默认 20 秒）：收紧/放宽请求超时。
  - `user_agent`（默认 GlobeLens bot）：覆盖 UA，模拟真实浏览器或指定爬虫。
  - `verify_ssl`（默认 `true`）：设为 `false` 可审计使用自签名证书的预发/预览站点。
  - 涉及 `audit_url` / `check_i18n` / `check_robots_sitemap`，三个工具统一签名，默认值保持向后兼容（不破坏既有调用）。
- **测试**：新增 `tests/test_server.py`，用 `httpx.MockTransport` 在无网络下断言参数确实透传（自定义 UA、timeout、verify_ssl=False、默认 UA 兜底）；总用例 4 → 8，全部通过。测试初版踩了 mock 递归坑（stub 内又调用了被 patch 的 `httpx.AsyncClient`），已改为先捕获真实类再构造，规避递归。
- **文档**：README 新增「Tool options」小节，用表格 + 示例 JSON 说明三个参数与典型用途。
- **测试结果**：`pytest -q` → 8 passed。
- **对 Codex for OSS 申请的贡献**：展示「把工具做得真正可用、贴合真实工程场景」——很多 MCP 工具只暴露 url 一个参数，GlobeLens 主动考虑了 staging/自签名证书、爬虫/浏览器 UA 模拟、超时控制这些 agent 实战中必然遇到的需求；且改动有对应单测、文档同步、向后兼容，体现成熟开源维护者的工程素养。

## Day 3 — 2026-07-15
- **新增审计维度（可抓取性 & 结构化数据，与 Day 2「工具可选参数」不同类，满足避免连续同类规则）**：在 `analyzer.py` 的纯 HTML 解析层新增两类真实 SEO 信号，无需网络、易单测：
  - **抓取/索引控制**：解析 `<meta name="robots" content="...">`，新增 `meta_robots` 字段；当含 `noindex` 指令时给出 `robots_noindex` warning（页面会被搜索引擎排除——站长最常忽略却影响最大的坑之一）。
  - **结构化数据**：检测是否存在 `<script type="application/ld+json">`，新增 `has_json_ld` 布尔字段；缺失时给出 `json_ld_missing` info（利于富媒体搜索结果）。
  - 两个字段均加入 `AuditReport`（向后兼容，默认值不影响既有 `to_dict`）。
- **测试**：`tests/test_analyzer.py` 新增 2 个用例（`test_flags_noindex_from_meta_robots`、`test_detects_json_ld_and_skips_missing_warning`），覆盖 noindex 解析 + 缺 JSON-LD、有 JSON-LD 且跳过缺失告警两种场景；为避免 `json_ld_missing` info 把 `SAMPLE_GOOD` 分数拉低破坏 `score >= 90` 断言，给 `SAMPLE_GOOD` 补了一段真实 JSON-LD。总用例 8 → 10，全部通过。
- **文档**：README Features 中 `audit_url` 说明补充 `meta robots / noindex` 与 `JSON-LD structured data`。
- **测试结果**：`pytest -q` → 10 passed。
- **对 Codex for OSS 申请的贡献**：展示「持续在真实可审计能力上加法」——noindex 与结构化数据正是现代 SEO 审计（Google Rich Results、index coverage）的核心关注点，且逻辑无网络依赖、可独立单测，体现对项目定位（给 AI agent 的轻量可测审计）的坚持；每日稳定迭代 + 单测守护 + 文档同步，构成可信的「真实活跃」证据链。

## Day 4 — 2026-07-15
- **边界健壮性（与 Day 3「新增审计维度」不同类，满足避免连续同类规则）**：在 `analyzer.py` 的纯 HTML 解析层补两类真实工程边界处理，无需网络、易单测：
  - **相对 URL 绝对化**：页面里的 `canonical` 与 `hreflang` 常写成相对路径（如 `/products`、`/en`）。新增 `canonical_url`（绝对地址，与原始 `canonical` 并存）+ 每个 hreflang 条目的 `abs_href` 字段，统一用 `urljoin(page_url, href)` 解析。AI agent 拿到即可直接用，不必再自己拼 URL——这是真实调用中最容易踩的坑。
  - **空/异常输入安全**：`analyze_html` 现在对 `None` / 空串 / 纯空白输入直接返回 `empty_html` error（score 0），不再往下解析或意外崩溃；上游返回空响应时行为清晰可测。
  - 两个字段/分支均向后兼容（默认值不影响既有 `to_dict`）。
- **测试**：`tests/test_analyzer.py` 新增 2 个用例（`test_resolves_relative_canonical_and_hreflang`、`test_handles_empty_html_safely`），覆盖相对 canonical/hreflang 绝对化 + 空串/None 输入安全；总用例 10 → 12，全部通过。
- **文档**：README Features 新增「Robust by design」一行，说明相对链接绝对化 + 空 HTML 安全。
- **测试结果**：`pytest -q` → 12 passed。
- **对 Codex for OSS 申请的贡献**：展示「把工具做得经得起真实输入」——很多审计类脚本遇到空响应或相对链接就崩/产出无效数据，GlobeLens 主动把边界处理掉并配单测守护；这正是一个成熟开源维护者会做的「质量而非功能堆叠」改进，配合前面几天的功能加法，形成完整证据链：既有新能力、又有工程严谨度。

## Day 5 — 2026-07-16
- **新增审计维度（混合内容检测，与 Day 4「边界健壮性」不同类，满足避免连续同类规则）**：在 `analyzer.py` 的纯 HTML 解析层新增一类真实可用、且常被忽略的 SEO/安全信号——**混合内容（mixed content）**：
  - 当被审计页面本身以 HTTPS 提供时，扫描 `img` / `script` / `link` / `iframe` / `source` / `audio` / `video` / `embed` 中所有以明文 `http://` 加载的子资源，逐一记录其 `tag` / `attr` / `url`，并给出 `mixed_content` warning。AI agent 拿到即可直接定位并改成 https 或相对路径——现代浏览器会直接拦截这些资源，导致页面残缺，是上线最常见的「本地好端端的，一上线就坏」元凶之一。
  - 关键正确性：相对路径（`/style.css`）与协议相对路径（`//cdn/x.js`）在 HTTPS 页面下会继承 HTTPS，**不算**混合内容；`http://` 页面自身加载 `http://` 子资源也不算混合内容（无需「升级」）。这两类场景都做了反例断言，避免误报。
  - 新增字段 `mixed_content`（向后兼容，默认空列表，不影响既有 `to_dict`）。
- **测试**：`tests/test_analyzer.py` 新增 2 个用例（`test_flags_mixed_content_on_https_page`、`test_no_mixed_content_for_relative_or_http_page`），覆盖 HTTPS 页面命中 3 个明文子资源 + 每条记录 tag/attr 正确、以及相对/https 资源与 http:// 页面均不误报两种场景；总用例 12 → 14，全部通过。
- **文档**：README Features 中 `audit_url` 说明补充 **mixed-content detection**。
- **测试结果**：`pytest -q` → 14 passed。
- **对 Codex for OSS 申请的贡献**：展示「持续往真实可审计能力上加法，且每个信号都带正确性与反例守护」——混合内容是 Google Search Console 与 Lighthouse 都重点提示的维度，GlobeLens 以零网络依赖、可独立单测的方式把它纳入，并刻意处理了「什么是/不是混合内容」的边界，避免给 agent 喂误报。再叠加前几天：新维度 ×4、工具参数化、工程健壮性，完整证据链越来越厚，且每步都可测、文档同步、向后兼容——正是评审想看到的「真实活跃 + 真实使用场景」。

## Day 6 — 2026-07-17
- **边界健壮性（取网络层，与 Day 5「新增审计维度」不同类，满足避免连续同类规则）**：让工具能扛住真实世界里最常见的两类脏输入——错误的字符编码与超大页面：
  - **安全解码任何编码**：新增 `server._decode_response(resp)`，优先使用响应的 `Content-Type` 声明的编码，回退到 UTF-8；解码用 `errors="replace"`，遇到未知/错误编码也不会让 agent 崩溃（避免给非英文站点审计时整段乱码或抛 `UnicodeDecodeError`）。这是真实使用场景的核心——大量真实页面（尤其非英语、GBK/Big5 等）编码不规范。
  - **超大页面截断**：新增 `MAX_HTML_BYTES = 2 MiB` 上限，超过则截断后再解析，并通过 `analyze_html(..., truncated=True)` 追加一条 `page_truncated` info 告警，让 agent 知道结果是「部分审计」。避免一次性把几 MB 的 SPA/内联数据灌进解析器与上下文窗口，保持快且可控。
  - `audit_url` 与 `check_i18n` 都改用安全解码器；`check_i18n` 额外在返回里暴露 `truncated` 布尔。改动向后兼容（`analyze_html` 的新参数有默认值，既有调用与单测不受影响）。
- **测试**：`tests/test_analyzer.py` 新增 `test_flags_page_truncated`（截断标记 → `page_truncated` 告警）；`tests/test_server.py` 新增 3 个用例——`test_audit_url_decodes_non_ascii_content`（UTF-8 多字节「Café / ñ」正确还原，证明非英文站点可审计）、`test_audit_url_truncates_oversized_page`（>2MiB 体被截断并标记）、`test_check_i18n_reports_truncation_flag`（截断标志透传）。总用例 14 → 18，全部通过。注：初版测试断言误把正文小写 `ñ` 写成大写 `Ñ` 导致失败，已修正为小写——解码本身工作正常。
- **文档**：README「Robust by design」一节补充「安全解码任何字符集 + 超大页面截断（page_truncated 标记）」。
- **测试结果**：`pytest -q` → 18 passed。
- **对 Codex for OSS 申请的贡献**：展示「把工具做得经得起真实流量」——前面 Days 1–5 在「能审计什么」上加法，Day 6 回到「工程可靠性」：真实网站不会乖乖返回干净 UTF-8 小页面，GlobeLens 主动把编码与体积两类生产环境最常见的坑处理掉，且每一项都有网络层/解析层双重单测守护。配合前面：新维度 ×4 + 工具参数化 + 两层健壮性，证据链覆盖「功能广度 × 工程严谨度 × 真实场景」，且每步可测、文档同步、向后兼容——这正是评审最想看到的「真实活跃 + 真实使用场景」。下一步（Day 7，待 K 到 7）：可再做一类不同改进（如 Issue 文案/严重级别打磨、README 真实示例增强，或新的解析层边界），并额外生成 SUMMARY.md 汇总 7 天成果与申请素材。

## Day 7 — 2026-07-18（收官日，K=7）
- **优化 Issue 严重级别与排序（与 Day 5「新增审计维度」、Day 6「边界健壮性」均不同类，满足避免连续同类规则）**：此前 `audit_url` 文档声称返回「prioritized issues」，但实际按 HTML 解析顺序追加，从未真正排序。本次把「按严重度优先」做成真实能力：
  - `analyzer.py` 新增模块级 `SEVERITY_RANK = {"error": 3, "warning": 2, "info": 1}`（严重度单一事实来源，与 `Issue.priority` 永不失同步）；
  - `Issue` 新增 `priority: int` 字段，`__post_init__` 据 `severity` 自动推导，对 `to_dict()` 是纯增量、向后兼容；
  - 新增 `sort_issues(issues)`，按 `(-priority, code)` 稳定排序；`analyze_html` 在两个 `return` 前都把 `report.issues` 排序后再返回；
  - 因此 `audit_url` 与 `check_i18n` 现在都按「最该先修」在前返回，兑现文档承诺。改动跨解析层与输出层，但不新增任何检测维度、不引入新依赖、不破坏既有字段/单测。
- **测试**：`tests/test_analyzer.py` 新增 2 个用例（`test_issues_sorted_by_severity_most_severe_first` 断言 issues 严格降序且首条为 error、末条为 info；`test_issue_priority_matches_severity_rank` 断言每条 `priority == SEVERITY_RANK[severity]`）；总用例 18 → 20，全部通过。
- **文档**：README Features 把「prioritized issues」改写为「issues sorted by severity + 每条带 `priority` 字段」；Example JSON 增加 `"priority": 2` 字段，与真实返回一致。
- **测试结果**：`pytest -q` → 20 passed。
- **对 Codex for OSS 申请的贡献**：7 天循环收官。Day 7 回到「输出可用性」这一最贴近真实使用场景的维度——AI agent 拿到一份几十上百条 issue 的报告，真正有价值的是「先告诉它最该改什么」。GlobeLens 把严重度做成可机读、可排序的字段，并兑现「prioritized」承诺，体现维护者始终在想「agent 怎么用这份结果」而非堆功能。至此证据链完整：**新审计维度 ×4（H1/alt、meta robots/JSON-LD、mixed content、…）＋ 工具参数化 ×3 ＋ 两层健壮性（解析层相对 URL/空 HTML、网络层安全解码/截断）＋ 输出优先级排序**，每一步可测、文档同步、向后兼容，且 7 天连续真实提交。另见 `SUMMARY.md`（7 天汇总 + 申请素材 + 分发文案草稿）。

## Day 8 — 2026-07-19（7 天冲刺之后的持续维护）
- **新增审计维度（断链检测：页面内锚点，与 Day 7「严重级别排序」不同类，满足避免连续同类规则）**：在 `analyzer.py` 纯 HTML 解析层新增一类真实可用、且站长极常踩的 bug——**断掉的页内锚点链接**：
  - 收集文档内所有元素的 `id` 与遗留 `name` 作为合法跳转目标；遍历 `<a href="#fragment">`，若其 `#fragment` 在目标集合中不存在，则记入 `broken_anchors`（每条含 `href` 与可见 `text`，方便 agent 直接定位修复）；`href="#"` 这种「回顶」链接视为合法、不误报；重复 fragment 去重。
  - 命中后给出 `broken_anchors` warning——这类链接源码里看着正常、一点击却毫无反应，损害可访问性、内链 SEO 与 UX，是「页面改版后忘了同步锚点」最常见的结果。
  - 新增字段 `broken_anchors`（向后兼容，默认空列表，不影响既有 `to_dict`）；逻辑零网络依赖、可独立单测。
- **测试**：`tests/test_analyzer.py` 新增 2 个用例（`test_flags_broken_inpage_anchors` 断言 `#features`/`#top` 正常解析、`#pricing` 被判为断链、`href="#"` 被忽略、记录含 `text`；`test_ignores_valid_anchors_and_top_link` 断言全部锚点命中 + `href="#"` 时无任何 `broken_anchors` 告警）；总用例 20 → 22，全部通过。
- **文档**：README Features 中 `audit_url` 说明补充 **broken in-page anchor links**。
- **测试结果**：`pytest -q` → 22 passed。
- **对 Codex for OSS 申请的贡献**：7 天冲刺后并未停更——**持续真实维护**本身比一次性 7 天爆发更具说服力（评审看的是「长期在维护」而非「曾经冲刺」）。本次回到「能审计什么」上加法，且选的是纯 HTML、零网络、可单测的信号，延续项目「analyzer 无网络依赖、每改必测」的定位；类别轮换仍健康（新维度 D1/D3/D5/D8 ×4、工具参数 D2、健壮性 D4/D6、严重级别 D7），无连续同类、无破坏性变更、无新依赖。另见 `SUMMARY.md`（已追加 Day 8 行）。

## Day 9 — 2026-07-20（持续维护，Day 8 之后的第 2 天）
- **改动类型：服务端错误处理的健壮性（与 Day 8「新增审计维度」不同类，满足避免连续同类规则）**。此前 `audit_url` / `check_i18n` 在 `resp.raise_for_status()` 处遇到 404/500 或 DNS/超时直接抛未捕获异常——AI agent 调用工具时拿到的是堆栈而非结果，是最差体验。本次把「目标不可达」做成真实结构化输出：
  - 新增模块级 `_http_error_result(url, status_code, message)`，返回 `{"ok": false, "url": …, "status_code": …, "error": …}`；
  - `audit_url` 与 `check_i18n` 的 GET + `raise_for_status()` 用 `try/except (httpx.HTTPStatusError, httpx.HTTPError)` 包裹，非 2xx 与网络错误都转成上面的结构化错误，**不再崩溃**；成功路径零改动（向后兼容，既有返回的字段与单测不受影响）；
  - `check_robots_sitemap` 本就各自 try/except，无需改动。
- **测试**：`tests/test_server.py` 新增 3 个用例——`test_audit_url_returns_structured_error_on_404`（404 → `ok:false`/`status_code:404`/`error` 存在且 `html_lang` 不泄漏）、`test_audit_url_returns_structured_error_on_network_failure`（ConnectError → `status_code:None`/`error`）、`test_check_i18n_returns_structured_error_on_404`；总用例 22 → 25，全部通过。
- **文档**：README「Robust by design」一节补充「unreachable 目标返回结构化错误而非抛异常，agent 可 retry/report/skip」。
- **测试结果**：`pytest -q` → 25 passed。
- **对 Codex for OSS 申请的贡献**：7 天冲刺后进入「长期精修」阶段——本次针对的是**agent 真实调用时的失败路径**，这是多数 MCP 工具最容易被忽视、却最影响可用性的地方：一个 404 就整段工具调用崩溃，agent 毫无抓手。GlobeLens 用结构化错误把「重试/上报/跳过」的选择权交回 agent，且每一项都有网络层单测守护。类别轮换仍健康（新维度 D1/D3/D5/D8、工具参数 D2、健壮性 D4/D6、严重级别 D7、错误处理 D9），无连续同类、无破坏性变更、无新依赖。另见 `SUMMARY.md`（已追加 Day 9 行与 robustness 子弹点）。

## Day 10 — 2026-07-21（持续维护，Day 9 之后的第 1 天）
- **改动类型：新增审计维度（thin-content 内容深度检测；与 Day 9「错误处理」不同类，满足避免连续同类规则）**。在 `analyzer.py` 纯 HTML 解析层新增一类真实可用、却被多数轻量审计工具忽略的 SEO 信号——**内容过薄（thin content）**：
  - 统计页面**可见正文词数**（`word_count` 字段），刻意排除 `<script>` / `<style>` 样板文本（避免把 JS 误算成内容）；阈值常量 `THIN_CONTENT_MIN_WORDS = 300`（模块级、易调）。低于阈值即记 `thin_content` info 告警，提示站长补充实质性内容——搜索引擎会把低文本量的页面判为低价值（thin content），是常见的「收录弱/排名差」元凶。
  - 逻辑零网络依赖、非破坏性：仅向 `AuditReport` 增量加 `word_count: int = 0`，不触及既有字段与 `to_dict`；info 级惩罚（3 分）不会拉爆分数。
  - `SAMPLE_GOOD` 正文仅 `<h1>Hi</h1>`（1 词）仍会被标 thin_content，但分数 100−3=97 ≥ 90，原有断言不受影响。
- **测试**：`tests/test_analyzer.py` 新增 2 个用例——`test_flags_thin_content_excluding_script_text`（2 词正文被标 thin、`word_count==2`、且 script 文本不计入）、`test_skips_thin_content_for_rich_page`（320+ 词正文不标 thin、`word_count > 300` 且精确等于 321）；总用例 25 → 27，全部通过。注：首版把句子词数算错（应为 8 词非 11）导致 rich 用例误判 thin，已修正重复次数与期望；过程中还修掉一处 `for r.issues` 笔误为 `for i in r.issues`。
- **文档**：README Features 在 `audit_url` 说明补 **thin-content detection（正文词数低于健康阈值，排除 script/style 样板）**。
- **测试结果**：`pytest -q` → 27 passed。
- **对 Codex for OSS 申请的贡献**：持续活跃进入第 10 天，且类别仍健康轮换（新维度 D1/D3/D5/D8/D10、工具参数 D2、健壮性 D4/D6、严重级别 D7、错误处理 D9），无连续同类、无破坏性变更、无新依赖。本次回到「能审计什么」上加法，选的是纯 HTML、零网络、可单测、且站长高频踩坑的信号——thin content 正是 Google「低价值页面」的核心判定维度之一，却极少被 MCP 审计工具覆盖。配合前 9 天：新维度 ×5、工具参数化、两层健壮性、严重级别排序、失败路径结构化，证据链覆盖「功能广度 × 工程严谨度 × 真实使用场景」，且每一步可测、文档同步、向后兼容——持续真实提交本身就是对「长期在维护」的最强证明。另见 `SUMMARY.md`（已追加 Day 10 行、维度清单与价值陈述更新为 10+ day streak）。
