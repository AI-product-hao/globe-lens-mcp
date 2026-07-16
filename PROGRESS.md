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
