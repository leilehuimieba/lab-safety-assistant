# Web Seed V3 预抓取报告

- 执行时间：2026-03-20
- 输入文件：`data_sources/web_seed_urls_v3_candidates.csv`
- 总链接数：18
- 可抓取数（`status=ok`）：13（72.2%）
- 非 `ok` 数量：5（27.8%）
- 被拦截率（`blocked/requires_auth`）：2（11.1%）
- 低质量率（`quality_score < 0.35`）：1（5.6%）
- 乱码疑似（`encoding_suspect=true`）：4

## 状态分布
- `ok`: 13
- `error`: 3
- `blocked`: 2

## Provider 分布
- `jina`: 13
- `direct`: 5

## 任务分配（collector / cleaner）
- `collector`: 5 条
- `cleaner`: 13 条

### collector 优先处理
- `WEBV3-001` | `error` | 临床实验室生物安全指南（WS/T 442-2024） | `manual_backfill_or_replace_source`
- `WEBV3-002` | `blocked` | 临床实验室生物安全指南（WS/T 442-2024）PDF | `manual_capture_with_access`
- `WEBV3-003` | `error` | 国家卫生健康委公告（2025年）第1号（涉高等级病原微生物实验室审查职责调整） | `manual_backfill_or_replace_source`
- `WEBV3-004` | `error` | 国家卫生健康委员会令第14号（2025） | `manual_backfill_or_replace_source`
- `WEBV3-012` | `blocked` | 关于加强高校实验室安全工作的意见（教技函〔2019〕36号） | `manual_capture_with_access`

### cleaner 重点处理
- `WEBV3-005`：`quality_score=0.2233`，建议 `manual_summary_and_fact_check`
- `WEBV3-007`：`encoding_suspect=true`，建议 `manual_clean_encoding_and_fact_check`
- `WEBV3-017`：`encoding_suspect=true`，建议 `manual_clean_encoding_and_fact_check`
- `WEBV3-018`：`encoding_suspect=true`，建议 `manual_clean_encoding_and_fact_check`

其余 `status=ok` 且无异常标记条目可走 `auto_clean_and_ingest_candidate`。

## 输出文件
- 状态表：`data_sources/web_seed_urls_v3_prefetch_status.csv`
- 报告：`docs/pipeline/web_seed_v3_prefetch_report.md`
- 原始结果：`artifacts/web_seed_v3_prefetch.json`（本地保留，不入库）

