# 周报（自动）2026-03-30

- 统计区间：`7 days ago` -> `now`
- 生成时间：`2026-03-30 03:57:02`

## 1. 协作活跃度

- 本周提交数：`67`
- 活跃贡献者：`1` (blaze)
- 数据收集相关提交：`15`
- 清洗相关提交：`0`
- 发布验收相关提交：`0`

## 2. 数据规模快照

- `document_manifest.csv` 行数：`15`
- `web_seed_urls.csv` 行数：`18`
- `pdf_special_rules.csv` 规则数：`1`

## 3. 最近提交摘要

- `1373fc9` 2026-03-30 blaze - feat: harden go-live with stability checks and production deploy templates
- `55a055a` 2026-03-30 blaze - feat: add go-live preflight automation for deployment readiness
- `87577df` 2026-03-30 blaze - feat: achieve prod release gate pass with failover and emergency stabilization
- `079a873` 2026-03-30 blaze - chore: refresh release gate dashboard and v8.1 gate summary
- `9f57353` 2026-03-30 blaze - feat: deliver release gate snapshot and v8.1 skill-based data package
- `040e4de` 2026-03-30 blaze - fix: mark HTTP-blocked prefetch results as non-ok and refresh v8 reports
- `7075316` 2026-03-30 blaze - feat: execute B/C priority roadmap with v8 refresh, low-confidence dashboard, and workflow automation
- `5bff059` 2026-03-30 blaze - feat: enforce quality metric thresholds in release policy and schema
- `8d2d4de` 2026-03-30 blaze - feat: enforce pre-eval health gate and timeout retry defaults in v7 demo chain
- `d4c3a33` 2026-03-30 blaze - feat: add timeout root-cause retry tool and wait-indexing gate for v7 demo chain
- `95ed608` 2026-03-29 blaze - feat: add v7 dify import chain, v8 expansion release, and deploy one-click scripts
- `2d79b8d` 2026-03-29 blaze - refactor: modularize core scripts into pipeline/release/qa with shims
- `3410fd9` 2026-03-29 blaze - chore: clean repo structure and remove legacy v1-v6 artifacts
- `802ad45` 2026-03-29 blaze - feat: ship v7 release pipeline and harden web demo fallback
- `fe97623` 2026-03-29 blaze - feat: ship v6.1 fetch recovery, low-quality rewrite, and demo api regression
- `466d725` 2026-03-29 blaze - feat: add v6 source batch with automated prefetch reporting
- `3411cf9` 2026-03-29 blaze - feat: add v5 one-click release pipeline and export bundle
- `c0498fe` 2026-03-29 blaze - feat: upgrade web demo APIs and add v5 data prefetch batch
- `193a124` 2026-03-29 blaze - feat(ops): auto-assign release fixes and escalate overdue P0 tasks
- `b013951` 2026-03-29 blaze - docs(ops): document release fix issue sync workflow

## 4. 最新发布验收状态

- 批次：`release-kb-20260318-v3`
- 审核日期：`2026-03-18`
- 审核人：`blaze` / `codex`
- 人工审核题数：`10`
- 通过题数：`0`
- 高风险错误建议：`0`
- 发布结论：`no`

## 5. 下周建议（自动）

- 建议优先补齐 `P0/P1` 数据来源，当前文档规模偏小。
- 本周缺少清洗提交，建议固定每周执行一次 PDF 体检与统一入库。
- 最新验收结论为 `no`，建议优先关闭高风险问题后再发布。
