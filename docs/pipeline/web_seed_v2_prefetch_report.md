# Web Seed V2 预抓取报告

- 执行时间：2026-03-18
- 输入文件：`data_sources/web_seed_urls_v2_candidates.csv`
- 总链接数：17
- 可抓取率：14（82.4%）
- 被拦截率：3（17.6%）
- 低质量率（阈值 `quality_score < 0.35`）：0（0.0%）

## 状态分布
- `ok`: 14
- `blocked`: 3

## Provider 分布
- `jina`: 17

## 需要人工补齐的条目（`status != ok`）
- `WEBV2-001` | `P0` | `blocked` | 高等学校实验室安全规范
- `WEBV2-016` | `P0` | `blocked` | 北京大学医学部实验室安全管理制度（PDF）
- `WEBV2-012` | `P1` | `blocked` | Safety Data Sheets and Certificates

## 任务分配建议
1. 信息收集员：优先处理 `P0` 且 `status != ok` 的来源，采用人工访问后摘要方式补齐。
2. 数据清洗员：对 `status=ok` 的条目执行统一清洗、切块和标签规范化。
3. 人工审核员：重点抽检高风险条目与临界质量分条目，确认事实准确性。

## 输出文件
- 候选源文件：`data_sources/web_seed_urls_v2_candidates.csv`
- 状态表：`data_sources/web_seed_urls_v2_prefetch_status.csv`
- 原始结果：`artifacts/web_seed_v2_prefetch.json`（本地保留，不入库）
