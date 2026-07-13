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
