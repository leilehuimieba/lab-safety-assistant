# V4.1 补链 + 改写复检总结（2026-03-27）

## 1. 目标

本轮执行目标：

1. 对 V1/V2/V3 中 `blocked/error` 的 10 条来源执行“官方替代链接”自动补链。
2. 对补链成功条目执行自动改写 + 复检。
3. 输出 `V1~V4.1` 升级版导入包。

## 2. 补链产物

- 补链映射表：`data_sources/relink_official_map_v4_1.csv`
- 自动补链脚本：`scripts/apply_official_relink.py`
- 补链后候选清单：
  - `data_sources/web_seed_urls_v1_1_candidates.csv`
  - `data_sources/web_seed_urls_v2_1_candidates.csv`
  - `data_sources/web_seed_urls_v3_1_candidates.csv`
- 补链报告：
  - `artifacts/relink_v4_1/official_relink_summary.md`
  - `artifacts/relink_v4_1/official_relink_details.csv`

## 3. 预抓取结果（补链后）

状态文件：

- `data_sources/web_seed_urls_v1_1_prefetch_status.csv`
- `data_sources/web_seed_urls_v2_1_prefetch_status.csv`
- `data_sources/web_seed_urls_v3_1_prefetch_status.csv`

10 条补链目标结果：

- `ok`：7 条
- `blocked`：2 条
- `error`：1 条

明细（见 `artifacts/relink_v4_1/relink_success_ids.csv`）：

- `ok`：`WEB-006`、`WEB-012`、`WEB-017`、`WEBV2-002`、`WEBV2-014`、`WEBV3-012`、`WEBV3-018`
- `blocked`：`WEBV2-001`、`WEBV2-012`
- `error`：`WEBV3-002`

说明：

- 本轮按“补链成功条目”进入改写复检，因此复检输入为 7 条。
- `WEBV2-001/WEBV2-012/WEBV3-002` 建议下一轮改为人工补录（PDF/截图转文本）或继续换源。

## 4. 自动改写 + 复检结果

复检运行目录：

- `artifacts/v4_1_repair_round/run_20260327_201226`

关键指标：

- baseline audit：`0/7` 通过（0.0）
- second audit（改写后）：`5/7` 通过（71.43%）
- second recheck：`5/5` 通过（100%）
- 审核通过增量：`+5`

关键文件：

- `artifacts/v4_1_repair_round/run_20260327_201226/repair_round_report.json`
- `artifacts/v4_1_repair_round/run_20260327_201226/rewrite/rewrite_log.csv`
- `artifacts/v4_1_repair_round/run_20260327_201226/second_recheck/knowledge_base_recheck_pass.csv`

## 5. V1~V4.1 升级导入包

输出目录：

- `artifacts/import_bundle_v12341`

导入主文件：

- `artifacts/import_bundle_v12341/knowledge_base_import_ready.csv`

报告：

- `artifacts/import_bundle_v12341/import_bundle_report.json`
- `artifacts/import_bundle_v12341/import_bundle_report.md`

当前总条目数：

- `304`

## 6. 后续建议（面向下一轮 V4.2）

1. 针对 `WEBV2-001/WEBV2-012/WEBV3-002` 建立人工补录清单（下载原文 PDF 后走统一清洗入库）。
2. 对 `v4_1_recheck` 未通过的 2 条（second audit 的 needs_fix）继续定向改写，再跑一次 recheck。
3. 将 `scripts/apply_official_relink.py` 接入一键流水线（`run_ai_oneclick_pipeline.py`）作为固定预处理步骤。
