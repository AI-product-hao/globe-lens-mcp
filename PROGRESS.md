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

## Day 11 — 2026-07-22（持续维护，Day 10 之后的第 1 天）
- **改动类型：补充单元测试覆盖新逻辑（与 Day 10「新增审计维度」不同类，满足避免连续同类规则）**。此前 OG/Twitter 卡片抓取、`robots_sitemap_urls` URL 推导、以及 `charset_missing` 分支虽早已实现，却只有「顺带」覆盖、没有专门断言——重构时极易悄悄退化而无人察觉。本次补齐 4 个针对性用例，把既有真实能力锁死：
  - `test_captures_og_and_twitter_card_tags`：断言 `og:title`/`og:description`/`og:image` 全链被抓进 `og_tags`，`twitter:card`/`twitter:title`/`twitter:description` 被抓进 `twitter_tags`，且两者齐备时 `og_missing` 信息不被误发（此前 `twitter_tags` 从未被任何测试验证过）。
  - `test_flags_missing_og_tags`：无 OG 标签时 `og_missing` info 必须触发。
  - `test_robots_sitemap_urls_across_url_shapes`：覆盖 origin / 深路径 / 非 https scheme / 带 query·fragment / 非标准端口 5 种 URL 形态，`robots.txt` 与 `sitemap.xml` 始终正确推导到 origin 根（该函数此前完全无单测）。
  - `test_flags_missing_charset`：无 `<meta charset>` 时 `charset is None` 且 `charset_missing` warning 触发（显式覆盖该分支）。
- **测试**：`tests/test_analyzer.py` 新增 4 例；pytest 27 → 31 passed。纯新增、零功能改动、零回归。
- **文档**：本日志与 `SUMMARY.md` 同步（SUMMARY 追加 Day 11 行、测试计数 27→31、价值陈述更新为 11+ day streak）。
- **对 Codex for OSS 申请的贡献**：持续活跃进入第 11 天，类别轮换仍健康（新维度 D1/D3/D5/D8/D10、工具参数 D2、健壮性 D4/D6、严重级别 D7、错误处理 D9、测试覆盖 D11），无连续同类、无破坏性变更、无新依赖。本次刻意「不做新功能、只把已有真实能力用测试钉死」——这恰恰是评审最看重却最稀缺的纪律：多数开源项目功能堆得快、测试跟不上，一旦重构就悄悄退化。GlobeLens 选择在第 11 天回补覆盖盲区（social 卡片、URL 推导 helper、字符集分支），证明维护重点是「长期可信」而非「功能数量」。配合前 10 天：新维度 ×5、工具参数化、两层健壮性、严重级别排序、失败路径结构化、测试覆盖加固，证据链覆盖「功能广度 × 工程严谨度 × 真实使用场景 × 测试纪律」，且每一步可测、文档同步、向后兼容——连续真实提交本身就是对「长期在维护」的最强证明。

## Day 12 — 2026-07-23（持续维护，Day 11 之后的第 1 天）
- **改动类型：新增审计维度（hreflang 值格式校验；与 Day 11「测试覆盖」不同类，满足避免连续同类规则）**。GlobeLens 此前只检测 hreflang 是否存在、是否缺 `x-default`，却从不校验每个 hreflang **值本身是否合法**。而「hreflang 值写错」恰是国际化站点最高频、最隐蔽的真实错误——搜索引擎会**静默忽略**非法值，本该生效的多语言/多地区替代版本因此完全丢失，站长却毫无提示。本次把这一维度补齐（纯 HTML、零网络、可单测，正中项目 i18n 定位）：
  - `analyzer.py` 新增模块级 `_HREFLANG_RE`（`^[a-z]{2,3}(-[a-z]{2}|-[0-9]{3})?$`，忽略大小写）+ `_is_valid_hreflang(code)` helper：接受 ISO 639-1 语言码（2–3 字母）可选叠加 ISO 3166-1 alpha-2 地区（2 字母）或 UN M.49 区域码（3 数字），并把保留关键字 `x-default` 特判为合法。
  - 在既有 hreflang 分支内收集所有非法值到新字段 `invalid_hreflang: list[str]`（向后兼容，默认空列表，不影响既有 `to_dict`），非空时给出 `hreflang_invalid` warning，消息直接列出错误值并给出正确示例（`en` / `en-US` / `x-default`），agent 拿到即可定位修复。
  - 精准命中真实高频错误：`en_US`（下划线而非连字符）、`english`（写成完整单词）、`en-USA`（地区 3 字母）全部判非法；`en` / `en-US` / `en-us` / `zh-CN` / `es-419` / `x-default` 均判合法，避免误报。
- **测试**：`tests/test_analyzer.py` 新增 2 例——`test_flags_invalid_hreflang_codes`（`en_GB`+`english` 命中、`en-US`+`x-default` 不误报、`invalid_hreflang` 精确等于 `{"en_GB","english"}`）、`test_accepts_well_formed_hreflang_codes`（`SAMPLE_GOOD` 的 `en`/`x-default` 全合法、无 `hreflang_invalid`）；pytest 31 → 33 passed，零回归。
- **文档**：README `check_i18n` 一行补充「hreflang value validation」并举例说明 `en_US` / `english` 会被标记及原因；`SUMMARY.md` 同步（追加 Day 12 行、测试计数 31→33、价值陈述更新为 12+ day streak）。
- **对 Codex for OSS 申请的贡献**：持续活跃进入第 12 天，类别轮换仍健康（新维度 D1/D3/D5/D8/D10/D12、工具参数 D2、健壮性 D4/D6、严重级别 D7、错误处理 D9、测试覆盖 D11），无连续同类、无破坏性变更、无新依赖。本次回到「能审计什么」上加法，且刻意选的是**最贴合项目 i18n 核心定位**、又被绝大多数轻量审计工具忽略的信号：hreflang 值合法性。它不是「有没有 hreflang」这种一眼可见的检查，而是「hreflang 写对了没有」这种源码看着正常、线上却静默失效的深层坑——正是 AI agent 在写国际化页面时最需要即时兜底的地方。配合前 11 天，证据链覆盖「功能广度 × 工程严谨度 × 真实使用场景 × 测试纪律」，每步可测、文档同步、向后兼容——连续 12 天真实提交本身就是「长期在维护」的最强证明。

## Day 13 — 2026-07-24（持续维护，Day 12 之后的第 1 天）
- **改动类型：边界 bug 修复 / 消除假阴性（与 Day 12「新增审计维度」不同类，满足避免连续同类规则）**。GlobeLens 的 charset 检测此前只认 HTML5 的 `<meta charset="utf-8">` 一种写法，却漏掉了同样合法、且在**老站与非英文站极其常见**的传统写法 `<meta http-equiv="Content-Type" content="text/html; charset=gb2312">`。结果这类页面明明声明了字符集，却被 GlobeLens 误报 `charset_missing`——这是一个真实的**假阴性**：工具冤枉了本来正确的页面，会误导 AI agent 去「修」一个不存在的问题。
  - `analyzer.py` charset 分支改为**同时接受两种写法**：优先 `<meta charset>`；缺失时回退查找 `http-equiv="Content-Type"`（大小写不敏感），并用正则 `charset\s*=\s*([^\s;]+)` 从其 `content` 中抽出字符集值写入 `report.charset`。仅当两种写法都无、`report.charset` 仍为空时才发 `charset_missing` warning。
  - 纯 HTML、零网络、非破坏性：不新增字段、不改既有 `to_dict`；HTML5 写法路径行为完全不变（向后兼容）。
- **测试**：`tests/test_analyzer.py` 新增 3 例——`test_reads_charset_from_http_equiv_content_type`（传统写法被识别、`charset=="gb2312"`、不再误报）、`test_html5_charset_still_wins_and_is_read`（HTML5 写法照常工作、`charset=="UTF-8"`）、`test_still_flags_charset_missing_when_neither_form_present`（两种都无时仍正确告警）。pytest 33 → 36 passed，零回归。
- **文档**：README「Robust by design」一节补充「charset 检测同时接受 HTML5 与 legacy http-equiv 两种写法，老站/非英文站不再被误报缺失 charset」。
- **测试结果**：`pytest -q` → 36 passed。
- **对 Codex for OSS 申请的贡献**：持续活跃进入第 13 天。本次修的是一个**真实假阴性**——不是加新功能，而是让既有检测「不冤枉正确的页面」。审计工具最伤信任的就是误报：一旦 agent 发现工具对合法页面报错，就会不再相信它的所有结论。GlobeLens 主动覆盖 HTML 规范里两种并存的 charset 写法（HTML5 + legacy http-equiv），正是「把工具做得经得起真实世界五花八门的写法」这一成熟维护心态的体现，且改动可测、文档同步、向后兼容。类别轮换仍健康（新维度 D1/D3/D5/D8/D10/D12、工具参数 D2、健壮性 D4/D6/D13、严重级别 D7、错误处理 D9、测试覆盖 D11），无连续同类、无破坏性变更、无新依赖——连续 13 天真实提交，「长期在维护」的证据链持续变厚。

## Day 14 — 2026-07-26（持续维护，Day 13 之后的第 1 天）
- **改动类型：新增审计维度（自引用 hreflang 检测；与 Day 13「边界 bug 修复」不同类，满足避免连续同类规则）**。Google 官方要求：hreflang 集群中的**每个页面都必须把自己也列为 alternate 之一**（self-referencing hreflang）；缺失自引用时，搜索引擎可能**静默忽略整个 hreflang 集群**——这是手工维护多语言站点时最高频、最隐蔽的真实错误之一：站长把 de/fr/es 都列全了，唯独忘了当前页面自己，源码看着一切正常，线上多语言映射却整体失效。本次把这一维度补齐（纯 HTML、零网络、可单测，正中项目 i18n 核心定位）：
  - `analyzer.py` 新增 `_self_ref_key(u)` helper：把 URL 归一化为 `(scheme小写, host小写, path去尾斜杠, query)` 四元组再比较——`https://example.com` 与 `https://example.com/` 视为同一页面，host 大小写不敏感，避免因写法差异误报。
  - `AuditReport` 新增字段 `hreflang_self_ref: bool | None`（`None` = 页面无 hreflang、检查不适用；`True`/`False` = 集群是否引用了页面自身），向后兼容、不影响既有 `to_dict`。
  - 比较基于每个 hreflang 条目**已解析的绝对地址** `abs_href`（复用 Day 4 的相对 URL 绝对化成果），相对写法 `href="/en"` 也能正确命中自引用。
  - 缺失自引用时给出 `hreflang_no_self_ref` warning，消息直接说明 Google 的要求与后果，agent 拿到即可补一条 `<link rel="alternate" hreflang="…" href="本页">`。
  - `server.py` 的 `check_i18n` 返回增加 `hreflang_self_ref` 字段；其 issue 过滤器本就按 `hreflang` 前缀匹配，新告警自动透出，零额外改动。
- **测试**：`tests/test_analyzer.py` 新增 4 例——`test_flags_missing_hreflang_self_reference`（/en 页面只列 de/fr → `False` + 告警）、`test_accepts_self_referencing_hreflang_with_normalization`（无尾斜杠页面 vs 带尾斜杠 x-default → 归一化命中、不误报）、`test_self_ref_resolves_relative_hreflang_and_host_case`（相对 `href="/en"` + 大写 host 均正确识别）、`test_self_ref_not_applicable_without_hreflang`（无 hreflang → `None`、永不误发）；pytest 36 → 40 passed，零回归。
- **文档**：README `check_i18n` 一节补充 self-referencing hreflang 规则说明；`SUMMARY.md` 同步（追加 Day 14 行、测试计数 36→40、价值陈述更新为 14+ day streak）。
- **测试结果**：`pytest -q` → 40 passed。
- **对 Codex for OSS 申请的贡献**：持续活跃进入第 14 天（两周整）。本次选的是**最贴合项目 i18n 定位、且被几乎所有轻量审计工具忽略**的信号：自引用 hreflang 不是「有没有写 hreflang」这种表层检查，而是 Google 文档明文要求、缺失即整簇失效的深层规则——正是 AI agent 在生成多语言页面时最容易犯、又最需要即时兜底的错误。实现上刻意做了 URL 归一化（尾斜杠/大小写/相对路径），并用 4 个正反例测试把「什么算自引用」的边界钉死，避免误报伤害工具信任。类别轮换仍健康（新维度 D1/D3/D5/D8/D10/D12/D14、工具参数 D2、健壮性 D4/D6/D13、严重级别 D7、错误处理 D9、测试覆盖 D11），无连续同类、无破坏性变更、无新依赖——连续 14 天真实提交，「长期在维护」的证据链持续变厚。

## Day 15 — 2026-07-26（持续维护，Day 14 之后的第 1 天）
- **改动类型：边界 bug 修复（重定向后的分析基准错误；与 Day 14「新增审计维度」不同类，满足避免连续同类规则）**。GlobeLens 的 HTTP 客户端一直开着 `follow_redirects=True`，但 `audit_url` / `check_i18n` 分析时仍把**请求 URL**（而非重定向后的**最终 URL**）当作页面基准。真实世界几乎每个站都有重定向（http→https、裸域→www、`/`→`/en/` 语言跳转），这个不匹配会造成三类静默错误：
  - 相对 `canonical` / `hreflang` 链接被 `urljoin` 到**错误的基准页**，产出错误的绝对地址；
  - Day 14 刚上线的**自引用 hreflang 检测被误报**：body 属于 `/en/`，却拿 `/old` 当「本页」比对，合法页面被判缺自引用——正是 Day 13 强调过的「误报最伤工具信任」；
  - 跨域重定向后 `robots.txt` / `sitemap.xml` 探测打到**旧主机**上，结果无意义。
- **修复**：`audit_url` / `check_i18n` 改用 `str(resp.url)` 作为分析与 robots/sitemap 推导基准；返回新增 `final_url`（实际分析的页面）与 `redirected`（bool，基于 `resp.history`）两个字段；`url` 字段仍回显调用方原始输入（向后兼容，既有断言不受影响）。工具 docstring 与 README「Robust by design」同步说明。
- **测试**：`tests/test_server.py` 新增 3 例——`test_audit_url_analyzes_against_final_url_after_redirect`（301 链：`/old`→`/en/`，断言 `final_url`/`redirected`/`canonical_url` 按最终页解析、`hreflang_self_ref is True` 且无 `hreflang_no_self_ref` 误报）、`test_audit_url_reports_no_redirect_for_direct_hit`（直连时 `redirected is False`）、`test_check_i18n_exposes_final_url_after_redirect`（check_i18n 同样透出并正确判定）。pytest 40 → 43 passed，零回归。
- **测试结果**：`pytest -q` → 43 passed。
- **对 Codex for OSS 申请的贡献**：持续活跃进入第 15 天。本次是一个**只有真实使用才暴露得出来的 bug**：单看代码「跟随重定向」和「解析相对链接」各自都对，组合起来却在几乎所有生产站点上产出错误结论——而且它直接侵蚀前一天刚交付的自引用检测的可信度。当天发现、当天修复、当天用 301 链单测钉死，同时把 `final_url`/`redirected` 透给 agent（审计结论对应哪个页面从此可追溯）。类别轮换仍健康（新维度 D1/D3/D5/D8/D10/D12/D14、工具参数 D2、健壮性/边界修复 D4/D6/D13/D15、严重级别 D7、错误处理 D9、测试覆盖 D11），无连续同类、无破坏性变更、无新依赖——连续 15 天真实提交，「长期在维护 + 会自我纠错」的证据链持续变厚。

## Day 16 — 2026-07-27（持续维护，Day 15 之后的第 1 天）
- **改动类型：改进 Issue 文案 / 输出可用性（给每条 issue 附带可执行修复提示；与 Day 15「边界 bug 修复」不同类，满足避免连续同类规则；上次同类是 Day 7 的严重级别排序，间隔充分）**。此前每条 issue 只说「哪里错了」（message），不说「怎么修」——agent 或人拿到 `hreflang_no_default` 还得先去查规则才能动手。本次把「怎么修」做成机器可读字段：
  - `analyzer.py` 新增模块级 `FIX_HINTS: dict[str, str]` 表——**24 个 issue code 全覆盖**，每条是具体、可直接照抄的修复动作（如 `charset_missing` → `Add <meta charset="utf-8"> as the first element inside <head>.`；`hreflang_no_default` → 给出完整 `<link rel="alternate" hreflang="x-default" ...>` 写法），而不是把问题换句话再说一遍。
  - `Issue` 新增 `fix: str = ""` 字段，`__post_init__` 按 `code` 自动从表中填充：显式传入的 fix 优先；未知 code 优雅降级为空串。对 `to_dict()` 纯增量、向后兼容，不影响任何既有字段与排序。
  - **防漂移守护**：新增一个「源码锁表」测试——用正则扫描 analyzer 源码里所有 `Issue(...)` 的 code，断言每个都在 `FIX_HINTS` 中。未来任何人新增审计维度却忘了配修复提示，测试套件直接红——message 与 fix 永不脱节。
- **测试**：`tests/test_analyzer.py` 新增 3 例——`test_every_emitted_issue_carries_actionable_fix_hint`（所有产出 issue 的 fix 非空、不等于 message 原文、且在 `to_dict()` 序列化后仍在；空 HTML 降级路径同样带 fix）、`test_fix_hints_cover_every_issue_code_in_analyzer`（源码锁表）、`test_explicit_fix_overrides_lookup_and_unknown_code_is_empty`（显式覆盖优先 + 未知 code 降级）。pytest 43 → 46 passed，零回归。
- **文档**：README Features 补「actionable `fix` hint」说明；Example JSON 增加 `"fix"` 字段与真实返回一致。
- **测试结果**：`pytest -q` → 46 passed。
- **对 Codex for OSS 申请的贡献**：持续活跃进入第 16 天。本次改的是**输出最后一公里**：审计工具的价值不在「报了多少问题」，而在「拿到报告能不能直接动手」。message + fix 的分离让 agent 无需二次检索规则即可修复——这正是「给 AI agent 用的审计工具」这一定位的字面兑现。工程上用单一事实来源表 + 源码锁表测试保证 24 个 code 的修复提示永不缺失、永不漂移，延续「每改必测、文档同步、向后兼容」的纪律。类别轮换仍健康（新维度 D1/D3/D5/D8/D10/D12/D14、工具参数 D2、健壮性 D4/D6/D13/D15、严重级别/文案 D7/D16、错误处理 D9、测试覆盖 D11），无连续同类、无破坏性变更、无新依赖——连续 16 天真实提交，「长期在维护」的证据链持续变厚。

## Day 17 — 2026-07-28（持续维护，Day 16 之后的第 1 天）
- **改动类型：工具可选参数（`max_bytes` 可配的 HTML 截断上限；与 Day 16「Issue 文案」不同类，满足避免连续同类规则；上次同类是 Day 2，间隔 15 天，多样性最大化）**。Day 6 引入的 2 MiB HTML 截断上限一直是硬编码：审计重型 SPA（内联了大量数据/组件的页面）的 agent **无法调高**拿到完整审计，想快速扫大页面的 agent 也**无法调低**换速度。本次把它做成真实可控的调用参数：
  - `audit_url` / `check_i18n` 新增可选参数 `max_bytes: int | None = None`（默认 `None` = 沿用 2 MiB，既有调用零变化、完全向后兼容）。
  - 新增 `MIN_HTML_BYTES = 1024` 下限 + `_effective_max_bytes()` helper：调用方传入低于 1 KiB 的荒谬值（如 `10`）时**向上钳制**而不是报错——1 KiB 以下连 `<head>` 都装不下，截出来的碎片只会产出纯噪声审计；钳制策略保证工具调用永远可用，延续「失败路径也要友好」的设计哲学。
  - `_decode_response()` 改为接受上限参数；截断**始终**通过 `page_truncated` issue（audit_url）与 `truncated` 标志（check_i18n）显式暴露——部分审计永不静默。
  - 工具 docstring 说明何时调高（重 SPA 完整审计）、何时调低（大页面快扫）；`check_robots_sitemap` 不解码 HTML 正文，无需此参数。
- **测试**：`tests/test_server.py` 新增 3 例——`test_audit_url_respects_custom_max_bytes`（48 KB 页面 + `max_bytes=2048` → 在自定义上限处截断并标记，且 head 在 2 KiB 内、核心字段照常解析）、`test_audit_url_clamps_max_bytes_to_floor`（`max_bytes=10` 被钳制到 1 KiB，正常小页面**不**被截断、title 完整）、`test_check_i18n_respects_custom_max_bytes`（check_i18n 同样生效并透出 `truncated: true`）。总用例 46 → 49，全部通过，零回归。
- **文档**：README「Tool options」表格新增 `max_bytes` 行（默认值、调高/调低场景、1 KiB 钳制、截断必标记），并补一条 heavy-SPA 示例调用 JSON。
- **测试结果**：`pytest -q` → 49 passed。
- **对 Codex for OSS 申请的贡献**：持续活跃进入第 17 天。本次是「把内部机制交给使用者控制」的典型改进：Day 6 为了工程安全定死的上限，在真实使用中会成为两类 agent 的天花板（要完整性的和要速度的），把它参数化正是「工具被真实使用后长出来的需求」。实现上刻意做了下限钳制而非抛错——工具参数设计的成熟度体现在「用户传错值时仍然给出可用结果」。类别轮换健康度极佳（新维度 D1/D3/D5/D8/D10/D12/D14、工具参数 D2/D17、健壮性 D4/D6/D13/D15、严重级别/文案 D7/D16、错误处理 D9、测试覆盖 D11），无连续同类、无破坏性变更、无新依赖——连续 17 天真实提交，「长期在维护」的证据链持续变厚。

## Day 18 — 2026-07-29（持续维护，Day 17 之后的第 1 天）
- **改动类型：新增审计维度（冲突的多重 canonical 检测；与 Day 17「工具可选参数」不同类，满足避免连续同类规则）**。Google 官方规则：当页面上存在**多个指向不同 URL 的 canonical 链接**时，搜索引擎会**直接忽略整页的 canonical 信号**——这是 CMS 迁移、模板拼接、插件各自注入 canonical 时最高频、最隐蔽的真实错误之一，源码看着「都有 canonical」一切正常，线上规范化却整体失效。本次把这一维度补齐（纯 HTML、零网络、可单测）：
  - `analyzer.py` 在 link 循环内收集所有 `rel="canonical"` 的 href（修复了此前**静默取最后一个**的隐性缺陷——现在明确以**第一条**为准记入 `canonical` / `canonical_url`）；按解析后的绝对地址**去重**后，若得到多个不同地址，则记 `canonical_conflict` warning，消息直接列出冲突 URL、说明搜索引擎会忽略冲突信号；新增 `canonical_urls: list[str]` 字段（绝对地址全量，向后兼容、不影响既有 `to_dict`）。
  - 关键正确性：**重复但指向同一地址**（如 `href="/"` 与 `href="https://example.com/"`）不算冲突——按绝对地址去重后只剩 1 个，不误报；只有真正指向不同 URL 才告警。
  - `FIX_HINTS` 同步补 `canonical_conflict` 修复提示（「只保留指向同一地址的单一 canonical」），源码锁表测试自动覆盖、无遗漏。
- **测试**：`tests/test_analyzer.py` 新增 2 例——`test_flags_conflicting_canonical_links`（两条 canonical 指向 `/` 与 `/home` → `canonical_conflict` 命中、`canonical_urls` 精确等于两个绝对地址、`canonical` 取第一条）、`test_ignores_duplicate_canonical_to_same_url`（相对/绝对重复 → 不误报、`canonical_urls` 仅剩 1 条）；pytest 49 → 51 passed，零回归。
- **文档**：README Features 在 `audit_url` 说明补 **conflicting `canonical` detection**；`SUMMARY.md` 同步（追加 Day 18 行、测试计数 49→51、价值陈述更新为 18+ day streak、维度清单加 canonical 冲突）。
- **测试结果**：`pytest -q` → 51 passed。
- **对 Codex for OSS 申请的贡献**：持续活跃进入第 18 天。本次选的是**最贴合项目 SEO 核心定位、且被几乎所有轻量审计工具忽略**的信号：canonical 冲突不是「有没有 canonical」这种表层检查，而是「多个 canonical 是不是指向同一个地方」这种源码看着正常、线上却让规范化整体失效的深层坑——正是 AI agent 在生成/改动页面模板时最需要即时兜底的错误。实现上同时修掉了旧代码「静默取最后一个 canonical」的隐性缺陷、做了绝对地址去重避免误报、用正反例双测试把边界钉死。类别轮换仍健康（新维度 D1/D3/D5/D8/D10/D12/D14/D18、工具参数 D2/D17、健壮性 D4/D6/D13/D15、严重级别/文案 D7/D16、错误处理 D9、测试覆盖 D11），无连续同类、无破坏性变更、无新依赖——连续 18 天真实提交，「长期在维护」的证据链持续变厚。

## Day 19 — 2026-07-30（持续维护，Day 18 之后的第 1 天）
- **改动类型：边界 bug 修复 / 消除误报（与 Day 18「新增审计维度」不同类，满足避免连续同类规则；上次同类是 Day 15，间隔充分）**。Day 8 上线的页内锚点断链检测有一个只在**非英文/i18n 站点**上暴露的误报：它拿 `href="#fragment"` 的**原始编码文本**去和元素 `id` 精确匹配，但真实世界的静态站生成器（MkDocs、Docusaurus、GitBook 等）对非 ASCII 标题锚点的处理几乎都是——`id` 保留字面文本（`id="快速开始"`），而 href 里写百分号编码（`href="#%E5%BF%AB%E9%80%9F%E5%BC%80%E5%A7%8B"`）。浏览器按 URL 规范会**先解码 fragment 再匹配 id**，所以这些锚点点击完全正常；GlobeLens 却全部误报为断链——对一个以 i18n 为核心定位的审计工具来说，这是最讽刺的一类假阳性：**中文/日文/带重音符文档站的合法锚点被成批冤枉**。
  - `analyzer.py` 断锚分支改为**原始与 `unquote()` 解码后的 fragment 双形态匹配**：任一命中目标集合即视为合法；去重也改按解码后形态进行——同一个缺失目标的编码写法与字面写法只产出**一条**记录，不再重复计数。
  - 关键正确性：解码**不掩盖真实断链**——编码 fragment 解码后仍无对应目标时照常告警；纯 ASCII 锚点路径行为完全不变（`unquote` 幂等），零回归风险。
  - 纯 HTML、零网络、零新依赖；不新增字段、不改 `to_dict`，完全向后兼容。
- **测试**：`tests/test_analyzer.py` 新增 2 例——`test_percent_encoded_anchor_matches_literal_id`（中文 + 带重音符 `café` 两种编码锚点均不误报）、`test_percent_encoded_anchor_still_flagged_when_target_missing`（解码后仍缺失的目标照常告警，且编码+字面双写法去重为 1 条记录）；pytest 51 → 53 passed，零回归。
- **文档**：README「Robust by design」一节补充「锚点匹配先做百分号解码（与浏览器行为一致），CJK/i18n 文档站的编码锚点不再被误报断链」。
- **测试结果**：`pytest -q` → 53 passed。
- **对 Codex for OSS 申请的贡献（Day 19）**：持续活跃进入第 19 天。本次延续 Day 13/15 确立的「误报最伤工具信任」维护哲学：一个审计工具冤枉合法页面一次，agent 就不再相信它的所有结论——而这个 bug 恰恰打在项目的核心用户群（做多语言出海站点的开发者）身上。修复对齐了浏览器真实行为（URL 规范的 fragment 解码），并用正反例双测试把「解码帮合法锚点洗冤、但不帮真断链开脱」的边界钉死。类别轮换仍健康（新维度 D1/D3/D5/D8/D10/D12/D14/D18、工具参数 D2/D17、健壮性/边界修复 D4/D6/D13/D15/D19、严重级别/文案 D7/D16、错误处理 D9、测试覆盖 D11），无连续同类、无破坏性变更、无新依赖——连续 19 天真实提交，「长期在维护 + 会自我纠错」的证据链持续变厚。

## Day 20 — 2026-07-31（持续维护，Day 19 之后的第 1 天）
- **改动类型：新增审计维度（`<html lang>` 值校验 + lang↔hreflang 语言一致性交叉检查；与 Day 19「边界 bug 修复」不同类，满足避免连续同类规则；上次同类是 Day 18）**。GlobeLens 此前对 `<html lang>` **只查有没有、从不查写没写对**——而这个属性正是浏览器、屏幕阅读器、翻译工具判断页面语言的唯一依据。更隐蔽的是：同一个页面对搜索引擎（hreflang）和对浏览器（lang）可以声明**两种不同的语言**，两边都「有值」、源码看着完全正常，却互相矛盾。本次把这两类真实错误补齐（纯 HTML、零网络、可单测，正中项目 i18n 核心定位）：
  - **共享 BCP 47 校验器**：新增 `_LANG_TAG_RE` + `_is_valid_language_tag()`，语法为「语言(2–3 字母) + 可选 ISO 15924 脚本(4 字母) + 可选地区(2 字母 / 3 数字)」；`_is_valid_hreflang()` 改为委托它（仅保留 `x-default` 特判）。**副带修正**：此前 hreflang 正则不认脚本子标签，`zh-Hans` / `zh-Hant-TW` 会被误判非法——正是中文站最常用的写法，现已接受。
  - **`lang_invalid`（warning）**：新增字段 `lang_valid: bool | None`（`None` = 无 lang，检查不适用）。`lang="english"` / `lang="en_US"` / `lang="en-USA"` 这类高频错误此前完全静默通过，现在直接命中——非法 tag 会被浏览器整个忽略，等同于没声明语言。
  - **`lang_hreflang_mismatch`（warning）**：新增字段 `lang_hreflang_mismatch: bool | None`。自引用检测改为收集**命中自身的 hreflang 条目**（复用 Day 14 的归一化比较），若其语言与 `<html lang>` 的**主子标签**不同即告警（例：/de 页面 `<html lang="en">` 但自引用 hreflang 是 `de`）。刻意只比主子标签，`en-US` vs `en-GB` 这种纯地区差异**不告警**；`x-default` 无语言含义、跳过；`lang` 本身非法时跳过比较而不是瞎猜——三处都是为避免误报做的边界收敛。
  - `server.py`：`check_i18n` 返回新增 `lang_valid` / `lang_hreflang_mismatch`；issue 过滤器由 `startswith("hreflang") or == "lang_missing"` 改为 `startswith(("hreflang", "lang"))`，新 code 自动透出。`FIX_HINTS` 同步补两条修复提示，源码锁表测试自动覆盖。
- **测试**：`tests/test_analyzer.py` 新增 5 例（非法 lang 命中且不重复报 `lang_missing`、`zh-Hans`/`zh-Hant-TW` 在 lang 与 hreflang 均不误报、真实 lang↔hreflang 冲突命中且消息含冲突语言、纯地区差异不误报且字段为 `False`、无 lang / 仅 x-default 自引用时两个字段均为 `None`）；`tests/test_server.py` 新增 1 例（`check_i18n` 透出 `lang_valid: false`、`lang_hreflang_mismatch: null`，且 `lang_invalid` 能通过新过滤器）。pytest 53 → 59 passed，零回归。
- **文档**：README Features 新增「🗣️ Language tag correctness」条目，说明 BCP 47 校验、脚本子标签支持、以及交叉检查规则与「地区差异不算冲突」的边界。
- **测试结果**：`pytest -q` → 59 passed。
- **对 Codex for OSS 申请的贡献（Day 20）**：持续活跃进入第 20 天。本次选的是**跨信号一致性**这类几乎没有轻量审计工具做的检查：单看 `lang` 合法、单看 `hreflang` 合法，只有把两者放在一起才发现页面在对浏览器和对搜索引擎说两种话——正是 AI agent 用模板批量生成多语言页面时最容易犯、人眼 review 最难发现的错误。实现上同时体现了两天前才强调过的克制：主子标签比较、x-default 跳过、lang 非法时不猜，三处都是宁可漏报也不误报的选择，并各有反例测试钉死。类别轮换仍健康（新维度 D1/D3/D5/D8/D10/D12/D14/D18/D20、工具参数 D2/D17、健壮性/边界修复 D4/D6/D13/D15/D19、严重级别/文案 D7/D16、错误处理 D9、测试覆盖 D11），无连续同类、无破坏性变更、无新依赖——连续 20 天真实提交，「长期在维护」的证据链持续变厚。

## Day 21 — 2026-08-01（持续维护，Day 20 之后的第 1 天）
- **改动类型：边界 bug 修复 / 消除误报（与 Day 20「新增审计维度」不同类，满足避免连续同类规则；上次同类是 Day 19）**。Day 10 上线的 thin-content 检测一直用 `re.split(r"\s+", text)` 统计正文词数——这个假设只对**用空格分词的语言**成立。中文、日文、泰文的正文**根本没有空格**：一篇 2000 字的中文文章会被算成 1–2 个「词」，于是**每一个中日泰长文页面都被稳定误报 `thin_content`**。这是一个比 Day 19 更严重的系统性假阳性：它不是偶发场景，而是对该语种站点 100% 命中，而这些站点恰恰是 GlobeLens 以 i18n 为核心定位所服务的主要人群——工具在告诉出海开发者「你的中文文章内容太薄」，纯属冤枉。
  - `analyzer.py` 新增 `_count_words(text)` 与两个可调常量 `CJK_CHARS_PER_WORD = 1.7`、`THAI_CHARS_PER_WORD = 4.5`，以及 `_NO_SPACE_SCRIPTS` 映射表（正则 → 每词字符数）：**无空格语种按字符计数后按各自比例折算成英文等价词数**（翻译行业通用换算），拉丁文本仍按空格切分，**混合语言页面两部分相加**（中英混排页面被公平计量）。
  - **刻意不纳入韩文**：谚文（Hangul）真实书写是**以空格分词**（eojeol），按字折算反而会高估词数——宁可保持既有正确行为，也不为了「看起来覆盖更全」而引入新的偏差。同理泰文虽同为无空格文字，但其平均词长远大于汉字，故单独给 4.5 的比例而非套用 1.7。
  - **顺带修掉一处噪声**：拆分后仅由标点构成的 token（CJK 的「。」「、」、导航分隔符 `|` `-` `•`）不再计为词——任何语言里标点都不是内容。
  - 纯 HTML、零网络、零新依赖；不新增字段、不改 `to_dict`，`word_count` 语义不变，完全向后兼容（纯 ASCII 页面计数结果与修复前逐字一致）。
- **测试**：`tests/test_analyzer.py` 新增 3 例——`test_counts_cjk_text_as_words_instead_of_false_thin_content`（694 汉字长文 → `word_count == 408` 且**不再**报 thin_content）、`test_counts_japanese_and_still_flags_a_genuinely_thin_cjk_page`（假名+汉字混排日文长文 `word_count == 428` 不报；同时断言**真正很短的中文页仍照常报 thin_content** —— 修复不能把检测本身消音）、`test_word_count_handles_mixed_scripts_thai_and_punctuation`（中英混排相加、泰文按自身比例、纯标点计 0、纯 ASCII 计数不变的回归守护）。pytest 59 → 62 passed，零回归。
- **文档**：README Features 的 thin-content 说明补「**script-aware**：中/日/泰无空格文字按字符计量而非算作一个词」；「Robust by design」一节同步补一句（与 Day 19 的锚点解码修复并列，形成「不冤枉 i18n 站点」的连续叙事）。
- **测试结果**：`pytest -q` → 62 passed。
- **对 Codex for OSS 申请的贡献**：持续活跃进入第 21 天（满三周）。本次修的 bug 有一个很强的说服力特征：**它只有在真正把工具用在非英语站点上才会暴露**，纯看代码或跑英文测试永远发现不了——`re.split(r"\s+")` 在任何 code review 里都长得人畜无害。GlobeLens 连续第二次（Day 19 锚点解码、Day 21 词数统计）主动清理打在自己核心用户群（做多语言出海站的开发者）身上的假阳性，延续 Day 13 确立的维护哲学：**审计工具误报一次，agent 就不再相信它的全部结论**。实现上继续体现克制——韩文不套用折算（会高估）、泰文单独比例（词长不同）、真短页仍照报（不为消除误报而牺牲检测力），三处取舍都有对应测试钉死。类别轮换仍健康（新维度 D1/D3/D5/D8/D10/D12/D14/D18/D20、工具参数 D2/D17、健壮性/边界修复 D4/D6/D13/D15/D19/D21、严重级别/文案 D7/D16、错误处理 D9、测试覆盖 D11），无连续同类、无破坏性变更、无新依赖——连续 21 天真实提交，「长期在维护 + 会自我纠错」的证据链持续变厚。

## Day 22 — 2026-08-02（持续维护，Day 21 之后的第 1 天）
- **改动类型：新增审计维度（`<meta http-equiv="refresh">` 客户端重定向 / 定时自刷新检测；与 Day 21「边界 bug 修复」不同类，满足避免连续同类规则；上次同类是 Day 20）**。GlobeLens 此前完整覆盖了服务端重定向（Day 15 的 `final_url` / `redirected`），却**完全看不见客户端重定向**——而 meta refresh 恰恰是国际化站点最常用的「按语言自动跳转」手段之一，也是老站迁移时最偷懒的替代方案。它有两副面孔，本次分开处理：
  - **带 `url=` 目标 → `meta_refresh_redirect`（warning）**：这是拿客户端跳转冒充真正的 HTTP 3xx。它必须等页面加载完才触发（用户会看到一次可见闪烁），且对搜索引擎而言是**比 301 弱得多的信号**——排名权重不一定能完整传给目标页。对 i18n 站点还有额外代价：爬虫被困在这个中转页上，真正的语言版本反而收录不到。
  - **不带目标 → `meta_refresh_reload`（info）**：页面每隔 N 秒把自己重新加载一遍。这是 **WCAG 2.2.1（Timing Adjustable）Level A 的明确失败项**——用户无法暂停、停止或延长，页面上填了一半的表单会被直接冲掉。刻意只给 info 级：仪表盘类页面确有合理的定时刷新场景，延续项目「宁可保守也不误伤」的取舍。
  - 新增字段 `meta_refresh`（原始 content）/ `meta_refresh_delay`（秒）/ `meta_refresh_url`（**已解析为绝对地址**的跳转目标，agent 拿到即可直接改成 301 的 Location），均为增量、向后兼容。`FIX_HINTS` 同步补两条修复提示，源码锁表测试自动覆盖、无遗漏。
  - **解析刻意做宽进严出**：真实世界的写法五花八门——`"0; url=/en/"`、`"5"`、`"0;URL='https://…'"`（大写 + 单引号）、甚至省略延迟的 `"url=/en/"`，正则对延迟、分隔符、引号、大小写全部宽容；但**不匹配的内容一律忽略而不是猜**（如 `content="not a refresh directive"` 不会被脑补成一次重定向）——绝不凭空捏造一个不存在的跳转。
- **测试**：`tests/test_analyzer.py` 新增 3 例——`test_flags_meta_refresh_redirect_and_resolves_target`（相对目标 `/en/` 解析为绝对地址、delay==0、两个 code 互斥只发其一、fix 提示含 301）、`test_flags_timed_self_reload_and_parses_quoted_uppercase_target`（无目标 → reload 命中且 `meta_refresh_url is None`；`content="5;URL='…'"` 大写 + 引号写法正确解析）、`test_no_meta_refresh_is_not_flagged_and_content_type_is_untouched`（干净页面零告警 + **回归守护**：相邻的 legacy `http-equiv="Content-Type"` charset 查找不被本次新增的 http-equiv 查找干扰，仍正确读出 `gb2312`，且垃圾 content 不被误判）。pytest 62 → 65 passed，零回归。
- **文档**：README Features 在 `audit_url` 说明补 **meta refresh detection**（含「带目标 = 该换 301」与「无目标 = WCAG 2.2.1」的区分）；`server.py` 的 `audit_url` docstring 同步；`SUMMARY.md` 追加 Day 22 行、测试计数 62→65、价值陈述更新为 22+ day streak。
- **测试结果**：`pytest -q` → 65 passed。
- **对 Codex for OSS 申请的贡献（Day 22）**：持续活跃进入第 22 天。本次补的是一处**能力版图上的空白而非细节打磨**：项目从 Day 15 起就认真处理服务端重定向，却一直对客户端重定向视而不见——一个页面明明会把访客甩到别处，审计报告里却只字未提，agent 据此得出的所有结论都建立在错误前提上。把它补齐之后，「这个页面到底会不会跳转、跳到哪」在报告里终于是完整的。实现上继续保持两点纪律：一是**把一个标签拆成两种语义**（重定向 vs 定时自刷新）而不是笼统报一条，因为二者的修法完全不同；二是**解析宽容但推断保守**——接受真实世界的各种写法，却拒绝对无法识别的内容做猜测，避免凭空产生假阳性（这已是 Day 13/19/21 反复强调的底线）。类别轮换仍健康（新维度 D1/D3/D5/D8/D10/D12/D14/D18/D20/D22、工具参数 D2/D17、健壮性/边界修复 D4/D6/D13/D15/D19/D21、严重级别/文案 D7/D16、错误处理 D9、测试覆盖 D11），无连续同类、无破坏性变更、无新依赖——连续 22 天真实提交，「长期在维护」的证据链持续变厚。

## Day 23 — 2026-08-03（持续维护，Day 22 之后的第 1 天）
- **改动类型：边界 bug 修复 / 消除误报（与 Day 22「新增审计维度」不同类，满足避免连续同类规则；上次同类是 Day 21）**。Day 5 上线的混合内容检测对 `<link>` 标签**一律取 `href` 判断是否 `http://`**——但 `<link>` 是 HTML 里语义最杂的标签：它既能加载真正的子资源（`stylesheet`、`icon`、`preload`、`manifest`），也大量用于**纯元数据与连接提示**（`canonical`、`alternate hreflang`、`prev`/`next`、`author`、`preconnect`、`dns-prefetch`）。后者浏览器**根本不会把它当页面子资源加载**，因此 `http://` 写法既不会被拦截、也不会触发混合内容警告。GlobeLens 却把它们统统记成不安全子资源——**误报**。
  - 打击面恰恰是本项目的核心用户：站点迁移到 HTTPS 后，`<link rel="canonical" href="http://…">` 与 `<link rel="alternate" hreflang="de" href="http://…">` 是最常见的历史遗留写法（它们确实该改成 https，但那是 canonical/hreflang 一致性问题，**不是** mixed content）。一个多语言站点光 hreflang 就能凭空刷出十几条假告警，把真正会被浏览器拦截的 stylesheet/icon 淹没在噪声里——**误报不只是不准，它会让真问题失去可见性**。
  - 修复：新增模块级 `FETCHING_LINK_RELS` 白名单（`stylesheet` / `icon` / `apple-touch-icon` / `apple-touch-icon-precomposed` / `mask-icon` / `fluid-icon` / `preload` / `modulepreload` / `prefetch` / `prerender` / `manifest`）+ `_link_fetches_subresource(tag)` helper；混合内容循环中 `<link>` 分支先过白名单，未命中直接跳过。**只跳过混合内容判定，不跳过标签本身**——canonical / hreflang 照常被解析进报告。
  - **顺带修掉一处隐性缺陷**：`_rel_values()` 在 rel 为字符串时直接整体小写返回（`"shortcut icon"` → `["shortcut icon"]` 单个元素），改为按空白切分。BeautifulSoup 通常已把 rel 解析成列表，但该 helper 也被 canonical/hreflang 分支复用，修好后多值 rel 在任何解析路径下都能正确匹配。
  - 关键正确性：**`preconnect` / `dns-prefetch` 刻意不列入白名单**——它们只预热 DNS/TCP、不取回任何内容，规范上也不属于混合内容；**`prefetch` / `prerender` 则列入**——它们会真实发起请求。这类「看着都是提示，其实一半会取数据」的区分，正是误报的来源。
  - 纯 HTML、零网络、零新依赖；不新增字段、不改 `to_dict`，`<link rel="stylesheet">` 等真实场景行为完全不变，完全向后兼容。
- **测试**：`tests/test_analyzer.py` 新增 2 例——`test_metadata_links_are_not_mixed_content`（HTTPS 页面上 canonical / 两条 hreflang / prev / next / preconnect / dns-prefetch / author / 无 rel 共 9 条 http 链接 → `mixed_content == []` 且无告警；同时断言 `canonical` 与 `hreflang` **仍被正常解析**，证明是「跳过判定」而非「跳过标签」）、`test_fetching_link_rels_are_still_flagged_as_mixed_content`（`stylesheet` / `shortcut icon` / `preload` / `manifest` 四条 http 链接照常命中，同页面的 http canonical 不被计入，`urls` 精确等于 4 条）。pytest 65 → 67 passed，零回归。
- **文档**：README「Robust by design」一节补充「混合内容扫描只看浏览器真会 fetch 的 `<link>` rel，`canonical` / `hreflang` / `prev`/`next` / `preconnect` 的 http 地址不再被误记为不安全子资源」。
- **测试结果**：`pytest -q` → 67 passed。
- **对 Codex for OSS 申请的贡献（Day 23）**：持续活跃进入第 23 天。本次是**连续第四次**（D13 charset、D19 锚点解码、D21 词数统计、D23 混合内容）主动清理误报，且这一条与前三条有个共同特征：**bug 都不在「检测逻辑对不对」，而在「检测对象选得对不对」**——代码本身运行完全正常，只是把一批不该进入判定范围的东西喂了进去，因此在任何 code review 和英文/单语测试里都长得人畜无害。本次还额外体现了一个真实工程判断：把 `<link>` 的 rel 按「是否真会发起请求」拆开，`prefetch` 算、`preconnect` 不算——这需要理解规范而不是照着标签名一刀切，也正是审计工具值得被信任的地方。类别轮换仍健康（新维度 D1/D3/D5/D8/D10/D12/D14/D18/D20/D22、工具参数 D2/D17、健壮性/边界修复 D4/D6/D13/D15/D19/D21/D23、严重级别/文案 D7/D16、错误处理 D9、测试覆盖 D11），无连续同类、无破坏性变更、无新依赖——连续 23 天真实提交，「长期在维护 + 会自我纠错」的证据链持续变厚。

## Day 24 — 2026-08-04（持续维护，Day 23 之后的第 1 天）
- **改动类型：工具可选参数（`follow_redirects` 开关；与 Day 23「边界 bug 修复」不同类，满足避免连续同类规则；上次同类是 Day 17，间隔 7 天）**。Day 15 起 GlobeLens 一律跟随重定向、并对**最终页**出报告——这个默认值是对的（相对链接、自引用 hreflang、robots 探测都依赖它），但它同时让一个真实问题**永远问不出来**：*这个 URL 自己到底做了什么？* 两个高频场景被挡死：
  - **站点迁移验收**：老 URL 该返回 **301（永久，传递权重）还是 302（临时，不传递）**，是 SEO 上的实质差别。跟随之后 agent 只看到目的页 200，状态码被吞掉，「迁移做对没有」无从验证。
  - **多语言路由验收**：`/` 按语言自动跳转到 `/en/` / `/de/` 时，跟随重定向意味着**每次都在审计某一个语言版本**，而「跳转本身对不对、跳去了哪」才是要查的东西——这恰是本项目 i18n 核心用户最常做的事。
- **实现**：`audit_url` / `check_i18n` 新增可选参数 `follow_redirects: bool = True`（默认行为零变化、完全向后兼容），透传给 httpx client；新增 `_is_redirect(resp)`（3xx **且带 Location**——304 Not Modified 是 3xx 但不是重定向，畸形 3xx 无处可去，都排除）与 `_redirect_stop_result()`：命中时**在 `raise_for_status()` 之前**返回 `{ok, url, status_code, redirect_to, followed_redirects, redirected, note}`。若不拦截，httpx 的 `raise_for_status()` 对 3xx 同样抛错，agent 只会拿到一条无用的「HTTP 301 错误」——把它变成一份**正面结果**才是这个参数的意义。`Location` 常写成相对路径（`/en/`），统一 `urljoin` 成绝对地址，agent 拿到即可直接再喂给 `audit_url`。两个工具的正常返回也增加 `followed_redirects` 字段，报告自解释。
  - **关键边界（本次最容易被忽略的一处）**：`audit_url` 内部的 robots.txt / sitemap.xml 探测复用同一个 client。若跟着页面一起停止跟随，`http→https`、`裸域→www` 这类**极常见的 robots.txt 重定向**会被判成 404，凭空产出「缺少 robots.txt」的假阴性——而爬虫本身是会跟随 robots.txt 重定向的。故两个探测请求显式加 `follow_redirects=True` 覆盖，**页面级选择不污染站点级结论**，并配了专门测试守护。
- **测试**：`tests/test_server.py` 新增 5 例——`test_audit_url_reports_redirect_without_following`（301 → `ok:true`/`status_code:301`/`redirect_to` 绝对地址，且断言 transport **只看到 `/old` 一个请求**证明确实没跳、报告字段不泄漏）、`test_audit_url_resolves_relative_redirect_location`（`Location: /en/` 相对头解析为绝对）、`test_robots_probe_still_follows_redirects_when_page_does_not`（页面不跟随、robots.txt 301 到 www 仍判定 `has_robots_txt: true`，同时页面本体照常审计）、`test_check_i18n_reports_redirect_without_following`、`test_following_redirects_stays_the_default`（默认值回归守护：不传参时照旧跟随、`final_url` 为目的页、无 `redirect_to`）。pytest 67 → 72 passed，零回归。
- **文档**：README「Tool options」表格新增 `follow_redirects` 行 + 示例 JSON；新增「Inspecting a redirect instead of following it」小节（301-vs-302 迁移验收、locale 路由验收两个真实场景 + 真实返回 JSON + robots 探测不受影响的说明）；两个工具 docstring 同步；`SUMMARY.md` 追加 Day 24 行、测试计数 67→72、价值陈述更新为 24+ day streak。
- **测试结果**：`pytest -q` → 72 passed。
- **对 Codex for OSS 申请的贡献（Day 24）**：持续活跃进入第 24 天。本次改动的性质值得单独说明：它不是补 bug、也不是加检测项，而是**把一个此前被硬编码的产品决策交还给使用者**——Day 15 为了正确性把「跟随重定向」定死，在真实使用中却成了两类验收工作的天花板。这类需求只有工具被**真正用起来**之后才长得出来，正是 Codex for OSS 想看到的「真实使用场景」的直接证据。工程上有两点延续了既有纪律：一是**把失败变成结果**（3xx 不是错误，而是提问者要的答案，所以在 `raise_for_status` 前截胡）；二是**参数的作用域要精确**——页面级的「不跟随」不该顺手改变站点级的 robots/sitemap 判定，否则一个新参数就悄悄引入了新的假阴性，与 D13/19/21/23 连续四次清理误报的努力自相矛盾。类别轮换仍健康（新维度 D1/D3/D5/D8/D10/D12/D14/D18/D20/D22、工具参数 D2/D17/D24、健壮性/边界修复 D4/D6/D13/D15/D19/D21/D23、严重级别/文案 D7/D16、错误处理 D9、测试覆盖 D11），无连续同类、无破坏性变更、无新依赖——连续 24 天真实提交，「长期在维护」的证据链持续变厚。

## Day 25 — 2026-08-05（持续维护，Day 24 之后的第 1 天）
- **改动类型：新增审计维度（外部 `target="_blank"` 链接安全检测；与 Day 24「工具可选参数」不同类，满足避免连续同类规则；上次同类是 Day 22）**。GlobeLens 此前能审计页内锚点（Day 8），却**完全看不见另一种更危险的链接形态**：`<a target="_blank">` 打开新标签页的链接。若其 `rel` 缺少 `noopener` / `noreferrer`，被打开的页面可通过 `window.opener` 反向操控原页面的 `location`（经典的「反向标签页劫持」reverse-tabnabbing 钓鱼向量），且会额外占用原页面的进程——这正是 Lighthouse 的 "unsafe links" 审计项。本次把这一维度补齐（纯 HTML、零网络、可单测）：
  - 只针对**跨源 http(s) 链接**判定：same-origin 链接无 opener 泄漏风险；`mailto:` / `javascript:` / 页内 `#anchor` 等非 http(s) 导航不构成泄漏，均显式跳过——刻意收窄判定边界，避免对普通站点误报（延续 D13/19/21/23「误报最伤工具信任」的底线）。
  - 已带 `rel="noopener"` 或 `rel="noreferrer"` 的链接直接跳过（含协议相对写法 `//other.com`：解析后判为跨源，但被 `noreferrer` 保护，仍不误报）；只有「跨源 且 无保护」的链接才记入新字段 `unsafe_blank_links`（含 `href` 与可见 `text`）并给 `unsafe_blank_link` warning。
  - 新增字段 `unsafe_blank_links`（向后兼容，默认空列表，不影响既有 `to_dict`）；`FIX_HINTS` 同步补 `unsafe_blank_link` 修复提示（「给每条跨源 `target="_blank"` 加 `rel="noopener noreferrer"`」），源码锁表测试自动覆盖、无遗漏。
  - 关键正确性：`page_origin` 仅在调用方 `url` 是 http(s) 且有 netloc 时才计算，否则**整体跳过判定**而非瞎猜——本地 `file://` 或不完整 URL 下绝不凭空产出告警。
- **测试**：`tests/test_analyzer.py` 新增 2 例——`test_flags_unsafe_external_blank_links`（一个 https 页面上 5 条链接：2 条跨源无保护命中、same-origin 1 条/已保护 1 条/`mailto:` 1 条均不误报，且 `unsafe_blank_links` 精确等于 2 条跨源链接）、`test_only_unprotected_cross_origin_blank_links_flagged`（无 target、same-origin、协议相对已受保护、唯一跨源无保护链接四种混合 → 仅该 1 条命中，`href` 精确等于预期）。pytest 72 → 74 passed，零回归。
- **文档**：README Features 在 `audit_url` 说明补 **unsafe external `target="_blank"` links**（Lighthouse unsafe links / reverse-tabnabbing）；`SUMMARY.md` 同步（追加 Day 25 行、审计维度清单加 unsafe blank links、测试计数 72→74、价值陈述与 X draft 2 更新为 25+ day streak）。
- **测试结果**：`pytest -q` → 74 passed。
- **对 Codex for OSS 申请的贡献（Day 25）**：持续活跃进入第 25 天。本次回到「能审计什么」上加法，选的是**既有现实危害、又几乎被所有轻量审计工具忽略**的信号：反向标签页劫持是真实的钓鱼入口，Lighthouse 专门列出，GlobeLens 把它以零网络、可单测的方式纳入。实现上继续体现一贯的克制——把「跨源 http(s) 且无保护」作为唯一判定条件，same-origin、非 http(s)、已受保护链接三种边界全部反例测试钉死，本地/不完整 URL 下直接不猜，避免凭空产生假阳性。类别轮换仍健康（新维度 D1/D3/D5/D8/D10/D12/D14/D18/D20/D22/D25、工具参数 D2/D17/D24、健壮性/边界修复 D4/D6/D13/D15/D19/D21/D23、严重级别/文案 D7/D16、错误处理 D9、测试覆盖 D11），无连续同类、无破坏性变更、无新依赖——连续 25 天真实提交，「长期在维护」的证据链持续变厚。

## Day 26 — 2026-08-06（持续维护，Day 25 之后的第 1 天）
- **改动类型：边界 bug 修复 / 探测准确性（与 Day 25「新增审计维度」不同类，满足避免连续同类规则；上次同类是 Day 23）**。GlobeLens 从 Day 0 起判断 robots.txt / sitemap.xml 是否存在，用的一直是 `status_code == 200`——这个假设只在「服务器对不存在的路径老老实实返回 404」时成立。而现代前端托管几乎全部不是这样：**Vercel / Netlify / Cloudflare Pages / 任何带 catch-all rewrite 的 SPA 部署，会把每一个未知路径都重写成 `index.html` 并返回 200**。于是 `/robots.txt` 与 `/sitemap.xml` 都「200 了」，GlobeLens 汇报两个文件齐全，实际上一个都没有。
  - 这是**方向最坏的一类误判**：前面 D13/D19/D21/D23 修的四次都是「冤枉了正确的页面」（吵闹但至少提醒了人），这次恰恰相反——**工具主动为一个真实存在的 SEO 缺陷开脱**，agent 看到 `has_robots_txt: true` 就不会再去建文件，缺陷被工具本身盖住。而且它 100% 命中本项目最核心的用户画像：用 Vercel/Netlify 部署 SPA 的独立开发者。
  - **修复**：新增 `_content_type()` / `_body_head()`（只取前 2 KiB 嗅探，不重复请求、不引入开销）/ `_is_html_response()` 三个 helper，按「Content-Type 是 html 类」或「正文开头是 `<!doctype html` / `<html` / `<head` / `<body`」识别 fallback 页；再据此实现 `_is_robots_txt()` 与 `_is_sitemap_xml()`，替换 `audit_url` 内部探测与 `check_robots_sitemap` 的 `status == 200` 判定。
  - **松紧刻意不对称，避免修出反向误报**：robots.txt 只要「200 且不是 HTML」就算存在——**空的 robots.txt 是完全合法的**（等于 allow all），拒绝它就会制造新的假阴性；sitemap 则要求更严，必须出现 `<urlset` / `<sitemapindex` 根元素，或至少 Content-Type 是 XML 类（任何合法 sitemap 必有其一，故精确而不苛刻）。
  - **顺带修掉一处语义错误**：`check_robots_sitemap` 探测失败（DNS/TLS/超时）时此前返回 `found: false`——把「网络不通」讲成「文件不存在」，会让 agent 去创建一个可能早已存在的文件。改为 `found: null`（unknown），与 `audit_url` 里 `has_robots_txt = None` 的既有语义对齐；同时增量暴露 `status_code`，让 agent 能自己看出「200 但被判为不存在」是软 200 而非工具抽风。
  - 另修 `dict[str, any]` → `dict[str, Any]`（此前误用内置函数 `any` 作类型，因 `from __future__ import annotations` 未在运行时暴露）。零新依赖、不改任何 issue code、不影响评分。
- **测试**：`tests/test_server.py` 新增 5 例——`test_audit_url_rejects_spa_fallback_html_as_robots_and_sitemap`（catch-all 站点两个探测均 200+HTML → 双双 `False`，同时断言页面本体照常审计）、`test_check_robots_sitemap_unmasks_soft_200_and_reports_status`（`found False` 但 `status_code` 仍为 200，软 200 可追溯）、`test_check_robots_sitemap_accepts_genuine_files`（真实 `text/plain` robots + `application/xml` sitemap 仍判存在，守护不许修成假阴性）、`test_empty_robots_txt_still_counts_as_present`（空 robots.txt 合法、照常算存在）、`test_check_robots_sitemap_reports_unknown_on_network_error`（ConnectError → `found is None` + `error`）。既有的 `test_robots_probe_still_follows_redirects_when_page_does_not`（301→www 后真实 robots 正文）继续通过，重定向路径零回归。pytest 74 → 79 passed。
- **文档**：README「Crawl readiness」条目改写，说明软 200 检测与 `found: true/false/null` + `status_code` 三态返回；「Robust by design」一节追加一段（与前四次误报清理并列）；`check_robots_sitemap` docstring 同步；`SUMMARY.md` 追加 Day 26 行、测试计数 74→79、价值陈述与 X draft 2 更新为 26 天 / 79 tests。
- **测试结果**：`pytest -q` → 79 passed。
- **对 Codex for OSS 申请的贡献（Day 26）**：持续活跃进入第 26 天。本次这个 bug 有一个很值得讲的性质：**它是随着世界变化而变旧的假设，而不是写错的代码**。`status == 200 → 文件存在` 在静态主机时代完全正确，是 catch-all rewrite 成为前端默认部署方式之后才悄悄失效的——这类 bug 不会有人提 issue（工具「看起来正常」，只是结论偏乐观），只有维护者真的把工具用在自己的现代部署上才会撞见。修复的方向也和前四次误报清理相反：D13/19/21/23 是让工具**别乱报**，Day 26 是让工具**别放过**——一个审计工具替真实缺陷背书，比它偶尔吵闹危险得多。实现上继续保持一贯的边界纪律：robots 从宽（空文件合法）、sitemap 从严（必须有根元素）、探测失败明确返回 unknown 而不是猜，三处取舍各有测试钉死。类别轮换仍健康（新维度 D1/D3/D5/D8/D10/D12/D14/D18/D20/D22/D25、工具参数 D2/D17/D24、健壮性/边界修复 D4/D6/D13/D15/D19/D21/D23/D26、严重级别/文案 D7/D16、错误处理 D9、测试覆盖 D11），无连续同类、无破坏性变更、无新依赖——连续 26 天真实提交，「长期在维护 + 会自我纠错」的证据链持续变厚。

## Day 27 — 2026-08-07（持续维护，Day 26 之后的第 1 天）
- **改动类型：补充单元测试覆盖新逻辑（与 Day 26「边界 bug 修复」不同类，满足避免连续同类规则；上次同类是 Day 11，间隔 16 天）**。此前多项**早已实现、却只有顺带覆盖、没有专门断言**的真实能力，一旦重构极易悄悄退化而无人察觉。本次补齐 6 个针对性用例，把既有真实行为锁死：
  - `test_legacy_a_name_attribute_is_a_valid_anchor_target`：验证 `<a name="top">` 作为遗留锚点目标被收集，只报真正缺失的 `#nowhere`——防止重构锚点收集时误把 `name` 当普通属性丢掉。
  - `test_mixed_content_covers_media_and_frame_subresources`：验证 `iframe` / `video` / `audio` / `source` / `embed` 的 `http://` `src` 均判为 mixed content（这些标签的必需属性都是 `src`），防止 Day 23 引入 `_link_fetches_subresource` 白名单改动后误吞这些标签。
  - `test_self_reference_respects_query_string_and_port`：用带 `?lang=en` 与 `:8443` 端口的样例，断言同查询 + 仅 host 大小写差异 → True、不同查询 → False、不同端口 → False——把 Day 14 归一化四元组（scheme/host/path/query）的 `query` 与 `port` 维度钉死。
  - `test_score_never_goes_negative_and_matches_the_penalty_table`：用 19 个 issue（总惩罚 161）的 worst-case，断言 `r.score == 0`（钳制在 0..100），并以 penalty 表反推 healthy 页分数——锁死评分口径。
  - `test_issue_order_is_deterministic_within_a_severity_tier`：断言同严重度内按 code 排序、重跑结果一致——锁死 Day 7 `sort_issues` 的稳定排序。
  - `test_report_is_json_serializable_for_mcp_transport`：用 `json.loads(json.dumps(r.to_dict()))` 验证报告可跨 MCP 边界序列化、且所有集合字段非空——MCP 工具返回值必须可 JSON 序列化，这是真实集成前提。
- **测试**：`tests/test_analyzer.py` 新增 6 例；pytest 79 → 85 passed。纯新增、零功能改动、零回归。
- **文档**：本日志与 `SUMMARY.md` 同步（SUMMARY 追加 Day 27 行、测试计数 79→85、价值陈述更新为 27+ day streak）。
- **对 Codex for OSS 申请的贡献**：持续活跃进入第 27 天，类别轮换仍健康（新维度 D1/D3/D5/D8/D10/D12/D14/D18/D20/D22/D25、工具参数 D2/D17/D24、健壮性/边界修复 D4/D6/D13/D15/D19/D21/D23/D26、严重级别/文案 D7/D16、错误处理 D9、测试覆盖 D11/D27），无连续同类、无破坏性变更、无新依赖。本次刻意「不做新功能、只把已有真实能力用测试钉死」——延续 Day 11 确立的纪律：多数开源项目功能堆得快、测试跟不上，一旦重构就悄悄退化。GlobeLens 选择在第 27 天回补覆盖盲区（legacy name 锚点、媒体标签混合内容、自引用 query/port 维度、评分钳制、确定性排序、JSON 序列化），证明维护重点是「长期可信」而非「功能数量」。配合前 26 天，证据链覆盖「功能广度 × 工程严谨度 × 真实使用场景 × 测试纪律」，且每一步可测、文档同步、向后兼容——连续 27 天真实提交，「长期在维护」的证据链持续变厚。

## Day 28 — 2026-08-08（持续维护，Day 27 之后的第 1 天）
- **改动类型：边界 bug 修复 / 消除假阴性（与 Day 27「测试覆盖」不同类，满足避免连续同类规则；上次同类是 Day 26）**。本次一次修掉**两个真实假阴性**——它们都属于 Day 26 之后确认的同一类最危险失效：**工具替真正有缺陷的页面背书**，agent 看到「没问题」就不会再查，缺陷被工具本身盖住。
  - **BUG A：内联 SVG 图标的 `<title>` 被当成页面标题。** 代码用 `soup.title` 取标题，但 html.parser 不区分命名空间，会返回**整棵树里第一个** `<title>`。现代页面到处是无障碍图标（`<svg><title>Close menu</title></svg>`），而 SPA 外壳的真实 `<title>` 常由 JS 运行时设置、**服务端 HTML 里根本没有**——于是 GlobeLens 报出 `title = "Close menu"`，并把本该是 **error 级 `title_missing`** 的致命缺陷降级成一条无关痛痒的 **warning 级 `title_short`**。浏览器与搜索引擎永远只认 HTML 命名空间的 `<title>`（SVG `<title>` 只是图形的可访问名）。
    - 修复：新增 `_page_title_tag(soup)` + `_FOREIGN_TITLE_PARENTS = {"svg", "math"}`，遍历所有 `<title>`、**跳过祖先里含 svg/math 的**，返回第一个真正的 HTML 标题；`analyze_html` 改用它替代 `soup.title`。
  - **BUG B：任意元素的 `name` 属性都被当作锚点跳转目标。** HTML 规范的「find a potential indicated element」只认两种目标：id 匹配，或**`<a>` 元素**的 name 匹配。但旧代码用 `soup.find_all(attrs={"name": True})` 全量收集——于是 `<meta name="description">`、`<input name="q">`、`<iframe name="preview">`、`<form name>`、`<select name>` 统统注册成合法锚点。后果：几乎**每一个**带 meta description 的页面上，`href="#description"` 这种真实断链都会被判为正常，Day 8 上线的断链检测在最常见的场景下形同虚设。
    - 修复：收集范围收窄为 `soup.find_all("a", attrs={"name": True})`；id 目标路径不变。
  - 两处均为纯 HTML、零网络、零新依赖；**不新增任何字段、不改 `to_dict`**，格式良好的页面行为逐字不变（完全向后兼容）。
- **测试**：`tests/test_analyzer.py` 新增 4 例，每个 bug 一正一反——`test_inline_svg_title_is_not_mistaken_for_the_page_title`（无真实 title 的 SPA 外壳 → `title is None`、`title_missing` 命中、`title_short` **不**出现）、`test_real_head_title_still_wins_over_svg_titles`（同时存在真实 title 与两个 SVG title → 取真实的，且零 title 类告警）、`test_non_anchor_name_attributes_are_not_valid_jump_targets`（meta/input/iframe 的 name → `#description`/`#search`/`#preview` 三条全部正确判为断链）、`test_anchor_name_and_ids_remain_valid_targets`（回归守护：`<a name="top">` 与 `id="install"` 仍是合法目标，即使同页存在同名 `<input name="install">` 也不受影响）。pytest 85 → 89 passed，零回归。
- **文档**：README「Robust by design」一节补充两句——页面标题只取 HTML `<title>`（内联 SVG 图标名永不冒充标题，SPA 外壳照常拿到 `title_missing`）、只有 `<a name="…">` 算遗留锚点目标（`<meta>`/表单控件/`<iframe>` 的 name 不再让死链看起来合法）；`SUMMARY.md` 同步（追加 Day 28 行、测试计数 85→89、价值陈述与 X draft 2 更新为 28 天 / 89 tests）。
- **测试结果**：`pytest -q` → 89 passed。
- **对 Codex for OSS 申请的贡献（Day 28）**：持续活跃进入第 28 天（满四周）。本次两个 bug 有一个共同的、很值得讲的性质：**它们都不是"检测逻辑写错了"，而是"用了一个看起来最自然的 API/写法"**——`soup.title` 和 `attrs={"name": True}` 在任何 code review 里都无可挑剔，只有把工具真正跑在现代真实页面（内联 SVG 图标、带 meta description 的普通页面）上才会暴露。方向上与 Day 26 一致、与 D13/19/21/23 相反：那四次是让工具**别乱报**，D26 与今天是让工具**别放过**——一个审计工具替真实缺陷开脱，比它偶尔吵闹危险得多，因为吵闹至少提醒了人，而背书会让人彻底停止追查。修复同时坚持了既有纪律：按 HTML 规范收窄判定范围而不是打补丁，且每个收窄都配一条反例测试，证明合法用法（真实 `<title>`、`<a name>`、`id`）一个都没被误伤。类别轮换仍健康（新维度 D1/D3/D5/D8/D10/D12/D14/D18/D20/D22/D25、工具参数 D2/D17/D24、健壮性/边界修复 D4/D6/D13/D15/D19/D21/D23/D26/D28、严重级别/文案 D7/D16、错误处理 D9、测试覆盖 D11/D27），无连续同类、无破坏性变更、无新依赖——连续 28 天真实提交，「长期在维护 + 会自我纠错」的证据链持续变厚。

## Day 29 — 2026-08-09（持续维护，Day 28 之后的第 1 天）
- **改动类型：新增审计维度（hreflang 集群完整性），与 Day 28「边界 bug 修复」不同类，类别轮换继续健康。** 此前 `check_i18n` 已经能抓「值非法 / 缺 x-default / 缺自引用」，但有个**结构性**漏洞没覆盖：即使每个 hreflang 值都合法、也有 x-default、也做了自引用，**整个 alternate 集合在语义上仍可能自相矛盾、被搜索引擎整体丢弃**。本类 bug 极常见而且**肉眼几乎看不出来**，因为它不是"漏写"，而是"写重了 / 指错了"。
  - **场景一 — 一个语言码指向多个 URL（`hreflang_conflict`）**：从别的语言整段复制 `<link>` 块时忘了改语言码，导致 `hreflang="de"` 同时指向 `/de` 和 `/de-at`。Google 对矛盾对直接丢弃，这条（以及同块里其它本来正确的）alternate 一起失效。
    - 实现：按 hreflang 值分组收集目标 URL，用与自引用检查相同的归一化（`_self_ref_key`，忽略大小写、尾斜杠、端口、query 差异），同一码下出现 >1 个不同目标即记为冲突，输出 `{hreflang, urls[]}`。
  - **场景二 — 多个语言码指向同一 URL（`hreflang_duplicate_url`）**：某语言（如 `fr`）还没翻译完、临时被指回英文页 `hreflang="fr" href="/en"`，于是 `/en` 同时被 `en` 和 `fr` 声明。翻译上线前整个集群处于失效状态。
    - 实现：按归一化 URL 分组收集语言码（`x-default` 与自身共享不算冲突），同一 URL 下出现 >1 个不同语言码即记为重复，输出 `{url, hreflang[]}`；**x-default 与 en 共指一个 URL 是合法降级，不报**，尾斜杠差异也归一化、不误报。
  - 两处均为纯 HTML、零网络、零新依赖；新增字段 `hreflang_conflicts` / `hreflang_duplicate_urls`，`to_dict` 透传，格式良好的页面（含 SAMPLE_GOOD）行为逐字不变（完全向后兼容）。
- **测试**：`tests/test_analyzer.py` +3 例——`test_flags_one_hreflang_code_pointing_at_several_urls`（`de` 双指向 → 命中 `hreflang_conflict` 且只报 `de` 不报 `en`）、`test_flags_several_languages_claiming_the_same_url`（`fr` 指回英文页 → 命中 `hreflang_duplicate_url`，而 x-default 共享英文 URL 与尾斜杠差异均**不**误报）、`test_clean_hreflang_cluster_reports_no_conflict`（`/de` vs `/de/` 等同 URL 不算冲突、SAMPLE_GOOD 仍零告警）；`tests/test_server.py` +1 例 `test_check_i18n_exposes_hreflang_cluster_conflicts`（断言 `check_i18n` 把两个结构化字段都透传、两条 issue code 都在、每条都带非空 `fix`）。pytest 89 → 93 passed，零回归。
- **文档**：README「i18n focus」一条在自引用说明后补两句，点明集群完整性检测（冲突码 / 重复目标）及其危害；`SUMMARY.md` 同步（追加 Day 29 行、测试计数 89→93、价值陈述与 X draft 2 更新为 29 天 / 93 tests）。
- **测试结果**：`pytest -q` → 93 passed。
- **对 Codex for OSS 申请的贡献（Day 29）**：持续活跃进入第 29 天（满四周 + 1）。本类改进最能体现「真实使用场景」那条证据：hreflang 矛盾是**开源社区、多语言 SaaS、国际化博客**最高发的 SEO 事故之一，且往往**页面看起来完全正常**——开发者复制粘贴 `<link>` 块、临时把未翻译语言指回主语言，都是日常操作。工具能在不抓包、不比对多个页面的前提下，直接从单页静态 HTML 里揪出"合法但自相矛盾"的集群，正是给 AI 编辑器里的 agent 用的杀手级能力。贡献点可讲：**连续 29 天真实提交 + 本次把 i18n 审计从"单值校验"升级到"集群结构校验"**，覆盖了一整类此前完全失明的缺陷；类别轮换依旧健康（新维度 D1/D3/D5/D8/D10/D12/D14/D18/D20/D22/D25/D29、工具参数 D2/D17/D24、健壮/边界修复 D4/D6/D13/D15/D19/D21/D23/D26/D28、严重级别/文案 D7/D16、错误处理 D9、测试覆盖 D11/D27），无连续同类、无破坏性变更、无新依赖——「长期在维护 + 能力持续变厚 + 会自我纠错」的证据链继续加长。

## Day 30 — 2026-08-10（持续维护，Day 29 之后的第 1 天）
- **改动类型：错误处理 / 输入校验（与 Day 29「新增审计维度」不同类，满足避免连续同类规则；上次同类是 Day 9，间隔充分）**。此前三类工具对「根本取不到的 URL」处理得很差：① `audit_url` / `check_i18n` 调用方少写 scheme（如 `example.com`、`localhost:3000`）时，httpx 报 "Request URL is missing an 'http://' or 'https://' protocol"，而真实的 `file:///etc/passwd` 也被同样的话术误导——其实 scheme 早就有，agent 会被骗去"加一个它已经有的 scheme"；② 更糟的是 `check_robots_sitemap("example.com")` 会把调用方拼写错误伪装成「两个 unknown 探测」，看起来像站点宕机；③ `http://[` 这类非法 URL 经真实 server 抛 `httpx.InvalidURL`，而 `httpx.InvalidURL` **不是** `httpx.HTTPError` 子类，原 `except httpx.HTTPError` 兜不住，直接逃逸为未处理异常（stack trace 而非结果）。本次把「开 socket 之前先校验调用方输入」做成真实能力：
  - `server.py` 新增 `_url_input_error(url)`：在开 socket 前依次校验空串 / `urlparse` 抛 `ValueError`（如 `http://[`）/ scheme 缺失（含 `localhost:3000` 这种 host:port 误判为 scheme，返回带 `suggestion="https://..."` 的修正 URL）/ 非 http(s) scheme（`file:`/`data:`/`ftp:` 明确错误信息，绝不误导去加 scheme）/ 缺 host / host 含空格；任一命中返回与 `_http_error_result` 同形的 `ok=false` 载荷（额外带 `suggestion` 字段）。用 `re` 的端口正则区分「host:port 缺 scheme」与「真正的非 http(s) scheme」。
  - 三个工具入口统一加 `bad_url = _url_input_error(url); if bad_url: return bad_url` 守卫——坏 URL 在开 socket 前返回，绝不发请求、绝不伪装成站点宕机。
  - 补 `except httpx.InvalidURL` 分支兜住客户端拒绝的 URL（与 `except httpx.HTTPError` 并列），把 `audit_url` / `check_i18n` 的失败路径彻底闭环为结构化错误。
  - 零新字段、零新依赖、成功路径零改动，完全向后兼容。
- **测试**：`tests/test_server.py` 新增 11 例——`_url_input_error` 单测 7 例（空串 / 缺 scheme 给 `suggestion` / `localhost:3000` 与 `example.com:8080/x` 的 host:port 误判给修正 URL / `file:`·`data:`·`ftp:` 报 unsupported scheme / 缺 host 与 host 含空格 / `http://[` 被 urlparse 捕获 / 合法 URL 返回 None）+ 三个工具坏 URL 守卫 3 例（用会断言失败的 client 工厂证明 AsyncClient 根本没被打开、`audit_url`/`check_i18n` 返回 `ok=false`+`suggestion`、`check_robots_sitemap` 返回 `ok=false` 而非两个 bogus 探测）+ 1 例 `except httpx.InvalidURL` 分支（MockTransport 抛 `httpx.InvalidURL`，断言仍是 `ok=false`+结构化 error）。pytest 93 → 104 passed，零回归。
- **文档**：README「Robust by design」一节补充「unfetchable URL 在开 socket 前被拒绝，带具体错误与修正建议」；`SUMMARY.md` 同步（追加 Day 30 行 + 更新概览注 + changelog 表 + 价值陈述 30+ day streak + X draft 2 改 104 tests）。
- **测试结果**：`pytest -q` → 104 passed。
- **对 Codex for OSS 申请的贡献（Day 30）**：持续活跃进入第 30 天（满一个月整）。本次把「失败路径也要友好」这一贯穿项目的主线再往前推一格：**错误不在"网络/服务端"，而在"调用方输入"时，也要给机器可读、能一步重试的结论**。具体打了三个真实痛点——一是 httpx 的通用错误信息对 `file://` 这类 case 是误导性错的（项目要的是"别用 file:// 审计"，不是"给它加 scheme"），二是 `check_robots_sitemap` 会把一个拼写错误伪装成"站点没有了两个文件"的严重误判，三是 `httpx.InvalidURL` 这个 Python httpx 的公开 API 事实（非 HTTPError 子类）此前会让任何被客户端拒绝的 URL 直接炸成 stack trace。修复后三个工具对任何非法 URL 都返回 `{ok:false, error, suggestion?}`，且**不浪费一次请求**。类别轮换仍健康（新维度 D1/D3/D5/D8/D10/D12/D14/D18/D20/D22/D25/D29、工具参数 D2/D17/D24、健壮/边界修复 D4/D6/D13/D15/D19/D21/D23/D26/D28、严重级别/文案 D7/D16、错误处理 D9/D30、测试覆盖 D11/D27），无连续同类、无破坏性变更、无新依赖——连续 30 天真实提交，「长期在维护 + 能力持续变厚 + 会自我纠错」的证据链持续加长。

## Day 31 — 2026-08-11（持续维护，Day 30 之后的第 1 天）
- **改动类型：边界覆盖率补全（消除漏报，与 Day 30「错误处理/输入校验」不同类，满足避免连续同类规则）**。GlobeLens 的混合内容检测此前只在 `src` / `href` 属性上找明文 `http://`，但响应式图片把候选源写进**单独的 `srcset` 属性**（如 `<img srcset="http://old-cdn/x.jpg 1x, https://cdn/y.png 2x">`）。`srcset` 里的 `http://` 条目和 `src` 里的完全一样会被浏览器拦截，却因为不在被扫描的属性上、被工具整体漏掉——这正是图片密集站、响应式站（做多语言出海站最常见的形态）最容易被漏报的一类真实混合内容。本次把这块空白补上：
  - `analyzer.py` 新增 `_srcset_urls(value)` helper（按逗号切分候选、取每段首个空白前 token、丢弃 `2x`/`640w` 这类描述符），在混合内容循环里对 `img` / `source` 额外扫 `srcset`，命中明文 `http://` 即记入 `mixed_content`（attr 标为 `srcset`、含完整 url）；`https://` 的 srcset 候选与 `https://` 的 `src` 一律不误报。
  - 纯 HTML、零网络、零新依赖；不改任何 issue code、不加字段（`mixed_content` 列表本就存在、向后兼容），`FIX_HINTS` 的 `mixed_content` 条目已天然覆盖 srcset 修复提示。
- **测试**：`tests/test_analyzer.py` 新增 1 例 `test_flags_mixed_content_in_srcset`（HTTPS 页上 `srcset` 含 http:// 旧 CDN + https:// 新 CDN、`picture`/`source` 的 http:// srcset 一并命中；断言两条 srcset 漏报全被抓、https 候选不误报、`len(mixed_content)==2`）；pytest 104 → 105 passed，零回归。
- **文档**：README 做了一件 31 天来**从未以主类做过**的事——新增「Real-world walkthrough」真实使用场景小节：给出一段可直接复制给 agent 的审计指令 + 一份真实（缩写）报告 JSON（含 `priority` 与 `fix` 字段），演示「审计 → 修最高优先级问题 → 重跑看分数上涨」的闭环；mixed-content 特性条目同步补「including `srcset` responsive images」。`SUMMARY.md` 同步（追加 Day 31 行、测试计数 104→105、价值陈述 31+ day streak、X draft 2 改 105 tests、审计维度清单补 srcset）。
- **测试结果**：`pytest -q` → 105 passed。
- **对 Codex for OSS 申请的贡献（Day 31）**：持续活跃进入第 31 天（满一个月 + 1）。本次有两个互相加强的看点：① 技术上补的是一个**只会在真实图片密集/响应式站上暴露**的漏报——这也是本项目核心用户群（做出海多语言站的开发者）最常见的页面形态，且它和 D13/D19/D21/D23/D26/D28 一脉相承，属于「让工具不漏掉真实缺陷」这一类（与「不误报」相对，同样危险：漏报会让真问题失去可见性）；② 文档上首次给出**可复制的真实使用场景闭环**，直接回应申请里最看重的「real usage scenarios」证据——一个审计工具光有功能清单不够，得让人一眼看懂「agent 拿去怎么用」。类别轮换仍健康（新维度 D1/D3/D5/D8/D10/D12/D14/D18/D20/D22/D25/D29、工具参数 D2/D17/D24、健壮/边界修复 D4/D6/D13/D15/D19/D21/D23/D26/D28/D31、严重级别/文案 D7/D16、错误处理 D9/D30、测试覆盖 D11/D27），无连续同类、无破坏性变更、无新依赖——连续 31 天真实提交，「长期在维护 + 能力持续变厚 + 会自我纠错 + 文档讲清真实用法」的证据链持续加长。
- **下一步（Day 32）候选（避开「边界覆盖率补全」，上次是 D31）**：① 新增审计维度（上次 D29，间隔 2 天：favicon 缺失、title 与 h1 重复度、canonical 指向 noindex 页）；② 工具可选参数（上次 D24，间隔 7 天）；③ 测试覆盖（上次 D27，间隔 4 天）；④ 改进 Issue 文案/输出可用性（上次 D16，间隔 15 天）；⑤ README 真实示例增强的延续（如加一份 Cursor/Claude Code 接入 GIF/步骤、或「真实站点审计前后对比」）。暂无已知 latent bug。

## Day 32 — 2026-08-12（持续维护，Day 31 之后的第 1 天）
- **改动类型：新增审计维度（favicon 存在性检测；与 Day 31「边界覆盖率补全」不同类，满足避免连续同类规则；上次同类是 Day 29，间隔 3 天）**。GlobeLens 此前从标题/描述/结构化数据一路审到混合内容、断链、unsafe blank links，却一直看不见一个最常被忘、修复成本最低的品牌信号——**favicon 缺失**。没有 favicon，浏览器标签、书签、以及会展示图标位的搜索结果里站点都缺乏品牌识别，而补一个 `<link rel="icon">` 不过一行。本次把这一维度补齐（纯 HTML、零网络、可单测）：
  - `analyzer.py` 新增 `has_favicon` 布尔字段（向后兼容，默认 `False`）+ 一段扫描：遍历 `<head>` 里所有 `<link>`，只要出现任一常规图标 rel（`icon` / `shortcut icon` / `apple-touch-icon` / `apple-touch-icon-precomposed` / `mask-icon` / `fluid-icon`）即视为「已声明」。这里刻意**不区分 rel 的具体写法**——`shortcut icon` 与 `apple-touch-icon` 只是风格选择、不是审计缺陷；且 canonical / stylesheet / 其它 link 绝不冒充 favicon（误报最伤工具信任）。
  - 未声明时给出 `favicon_missing` info 告警（icon 缺失不影响排名、纯品牌体验，故 info 级），并附「加 `<link rel="icon" href="/favicon.ico">`」的可执行 `fix` 提示；`FIX_HINTS` 同步补该条目（源码锁表测试自动覆盖，无遗漏）。零新字段破坏既有 `to_dict`、零新依赖。
  - `SAMPLE_GOOD` 补了一条 `<link rel="icon" href="/favicon.ico">`，作为真正「好页面」的对照组（与 json-ld/og 的前例一致），既守护该样本分数不被无谓拉低，也隐式验证正向路径。
- **测试**：`tests/test_analyzer.py` 新增 2 例——`test_accepts_favicon_link_as_present`（`<link rel="icon">` 与常见的 `rel="shortcut icon"` 两种写法都判 `has_favicon=True`、不发 `favicon_missing`）、`test_flags_missing_favicon`（无 icon link 时 `has_favicon=False` 且 `favicon_missing` 命中、severity==info、fix 含 favicon 提示；canonical/stylesheet 链接不会被误当 favicon）；pytest 105 → 107 passed，零回归（`test_detects_good_signals` 的 `score>=90` 仍稳，SAMPLE_GOOD 仅在 thin_content 上扣 3 分=97）。
- **文档**：README Features 的 `audit_url` 清单补 **favicon presence**；`SUMMARY.md` 同步（追加 Day 32 行、审计维度清单加 favicon、价值陈述与 X draft 2 更新为 32+ day streak / 107 tests）。
- **测试结果**：`pytest -q` → 107 passed。
- **对 Codex for OSS 申请的贡献（Day 32）**：持续活跃进入第 32 天（满一个月 + 2 天）。本次回到「能审计什么」上加法，选的是**ROI 极高、却几乎被所有轻量审计工具忽略**的信号：favicon 缺失不是「有没有」这种表层检查，而是「一个站点常忘、一行就能修、却天天在标签页/书签/搜索结果里丢品牌」的真实体验坑——正是 AI agent 在生成页面模板时值得即时兜底的错误。实现上延续一贯的克制：只认「是否声明过 icon」、不挑写法、绝不把 canonical/stylesheet 误当 favicon，并配正反例测试钉死边界。类别轮换仍健康（新维度 D1/D3/D5/D8/D10/D12/D14/D18/D20/D22/D25/D29/D32、工具参数 D2/D17/D24、健壮性/边界修复 D4/D6/D13/D15/D19/D21/D23/D26/D28/D31、严重级别/文案 D7/D16、错误处理 D9/D30、测试覆盖 D11/D27），无连续同类、无破坏性变更、无新依赖——连续 32 天真实提交，「长期在维护 + 能力持续变厚 + 会自我纠错 + 文档讲清真实用法」的证据链持续加长。
- **下一步（Day 33）候选（避开「新增审计维度」，上次是 D32）**：① 工具可选参数（上次 D24，间隔 8 天）；② 测试覆盖（上次 D27，间隔 5 天）；③ 改进 Issue 文案/输出可用性（上次 D16，间隔 16 天）；④ README 真实示例增强延续（如「真实站点审计前后对比」/ Cursor·Claude Code 接入 GIF 或步骤）；⑤ 边界 bug 修复（上次 D31，间隔 1 天，可放宽）。暂无已知 latent bug。

## Day 33 — 2026-08-13（持续维护，Day 32 之后的第 1 天）
- **改动类型：工具可选参数（与 Day 32「新增审计维度」不同类，满足避免连续同类规则；上次同类是 D24，间隔 9 天）**。GlobeLens 的 `audit_url` 每次调用都会顺带发两个额外 HTTP 请求（`/robots.txt` + `/sitemap.xml`），对**单次**审计是便宜又有用的，但当一个 agent 批量审计很多页面时，这就是 3 倍请求量——要么拖慢、要么把目标主机打进限流。这次把这个行为做成开关：新增参数 `probe_robots_sitemap: bool = True`（默认不变，完全向后兼容）。
  - `server.py`：`audit_url` 签名加 `probe_robots_sitemap`（紧跟 `follow_redirects`，与既有可选参数排在一起）；docstring 的 Args 补对应条目（说明设 `false` 时省两个请求、两个探测字段回落为 `null` = "not checked"）；把既有的两个 `robots/sitemap` 探测 `try/except` 块整体包进 `if probe_robots_sitemap:`——跳过时 `has_robots_txt` / `has_sitemap` 保持 dataclass 默认值 `None`（语义上诚实：没去查，而非"不存在"）。零新字段、零新依赖、成功路径零改动。
  - README：Tool options 表补 `probe_robots_sitemap` 一行（含「audit_url only」标注与 `null` 语义），示例 JSON 数组补一条 `{ "url": "https://example.com", "probe_robots_sitemap": false }`。
- **测试**：`tests/test_server.py` 新增 `test_audit_url_skips_robots_sitemap_probes_when_disabled`——用 `seen` 列表断言只发了 1 个请求（页面本身，无 robots/sitemap 探测）、`has_robots_txt is None` / `has_sitemap is None`、`html_lang=="en"`（页面仍被审计）；pytest 107 → 108 passed，零回归。
- **文档**：README Tool options + 示例同步；`SUMMARY.md` 增量更新（追加 Day 33 行、工具参数清单补 `probe_robots_sitemap`、价值陈述与 X draft 2 更新为 33+ day streak / 108 tests）。
- **测试结果**：`pytest -q` → 108 passed。
- **对 Codex for OSS 申请的贡献（Day 33）**：持续活跃进入第 33 天（满一个月 + 3 天）。本次属于「让工具在真实工作流里更好用」这一类——批量审计是 agent 用户最自然的用法之一，而 3 倍请求量会真实卡住它；把探测做成可关，是对**真实使用场景**的直接回应，且完全向后兼容（默认不破任何既有调用）。延续一贯克制：跳过时字段回落为 `null` 而非假阴性，绝不误导。类别轮换仍健康（新维度 D1/D3/D5/D8/D10/D12/D14/D18/D20/D22/D25/D29/D32、工具参数 D2/D17/D24/D33、健壮/边界修复 D4/D6/D13/D15/D19/D21/D23/D26/D28/D31、严重级别/文案 D7/D16、错误处理 D9/D30、测试覆盖 D11/D27），无连续同类、无破坏性变更、无新依赖——连续 33 天真实提交，「长期在维护 + 能力持续变厚 + 会自我纠错 + 文档讲清真实用法」的证据链持续加长。
- **下一步（Day 34）候选（避开「工具可选参数」，上次是 D33）**：① 测试覆盖（上次 D27，间隔 6 天）；② 改进 Issue 文案/输出可用性（上次 D16，间隔 17 天）；③ README 真实示例增强延续（如「真实站点审计前后对比」/ Cursor·Claude Code 接入 GIF 或步骤）；④ 边界 bug 修复（上次 D31，间隔 2 天，可放宽）；⑤ 新增审计维度（上次 D32，间隔 1 天，可放宽，避开已覆盖项）。暂无已知 latent bug。
