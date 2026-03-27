# Web Seed v4 预抓取报告

生成时间：2026-03-27  
输入清单：`data_sources/web_seed_urls_v4_candidates.csv`（11条，已移除不可访问的 `WEB4-010`）

## 1. 结果概览

1. 可抓取（`status=ok`）：11
2. 被拦截（`status=blocked`）：0
3. 抓取失败（`status=error`）：0
4. 可抓取率：100.0%
5. 被拦截率：0.0%
6. 失败率：0.0%

状态明细文件：`data_sources/web_seed_urls_v4_prefetch_status.csv`

## 2. 被拦截条目（当前）

当前无被拦截条目。

## 3. 下一步动作建议

1. 清洗员优先处理 11 条 `ok` 数据源，进入统一入库流程。
2. 一键跑批建议使用：
   - `scripts/run_ai_oneclick.ps1`
   - 并指定 `-WebManifest data_sources/web_seed_urls_v4_candidates.csv`
