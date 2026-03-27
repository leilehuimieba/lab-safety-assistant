# Web Seed v4 预抓取报告

生成时间：2026-03-27  
输入清单：`data_sources/web_seed_urls_v4_candidates.csv`（12条）

## 1. 结果概览

1. 可抓取（`status=ok`）：11
2. 被拦截（`status=blocked`）：1
3. 抓取失败（`status=error`）：0
4. 可抓取率：91.7%
5. 被拦截率：8.3%
6. 失败率：0.0%

状态明细文件：`data_sources/web_seed_urls_v4_prefetch_status.csv`

## 2. 被拦截条目（需人工补录）

1. `WEB4-010`
   - 标题：WHO Laboratory biosafety manual PDF
   - URL：`https://iris.who.int/bitstream/handle/10665/338380/9789240011311-eng.pdf`
   - 状态：`blocked`
   - 建议：收集员手动下载 PDF 后放入 `manual_sources/inbox/`，并在 `data_sources/manual_document_manifest.csv` 记录元数据。

## 3. 下一步动作建议

1. 清洗员优先处理 11 条 `ok` 数据源，进入统一入库流程。
2. 收集员先补录 `WEB4-010`，再由清洗员走 PDF 提取与 AI 审核链路。
3. 一键跑批建议使用：
   - `scripts/run_ai_oneclick.ps1`
   - 并指定 `-WebManifest data_sources/web_seed_urls_v4_candidates.csv`

