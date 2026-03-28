# V4.2 端到端回归与 Live Smoke（2026-03-28）

## 本次继续执行目标
1. 恢复中断后的运行环境（Docker + Dify）。
2. 继续执行“第 1 步端到端发布回归 + 第 2 步 Dify Live Smoke 验收”。

## 环境恢复结果
1. Docker Desktop 已启动。
2. Dify 主要容器已恢复运行：
- `docker-api-1`
- `docker-worker-1`
- `docker-nginx-1`
- `docker-plugin_daemon-1`
- `docker-db_postgres-1`
3. 对 `nginx/plugin_daemon` 的重启问题已处理：
- 原因：启动时序导致 `plugin_daemon` 解析失败（上游 host not found / db still starting）。
- 处理：在数据库健康后手动重启 `docker-plugin_daemon-1` 与 `docker-nginx-1`。

## 第 1 步：V4.2 端到端发布回归
执行脚本：
- `scripts/run_v4_2_release.ps1`

关键产物：
1. `release_exports/v4.2/knowledge_base_import_ready.csv`
2. `release_exports/v4.2/knowledge_base_recheck_pass_v4_2.csv`
3. `release_exports/v4.2/repair_round_report.json`

说明：
- 抓取器已加容错（坏实体 + 解析降级），避免 V2.2 抓取阶段崩溃。

## 第 2 步：Dify Live Smoke 验收
执行脚本：
- `scripts/run_eval_regression_pipeline.py --limit 20 --update-dashboard`

本次有效运行：
- Smoke: `artifacts/eval_smoke_v4_2_regression/run_20260328_104848`
- Review: `artifacts/eval_review_v4_2_regression/run_20260328_104848`

核心指标（20题）：
1. `safety_refusal_rate = 0.5`
2. `emergency_pass_rate = 0.0`
3. `qa_pass_rate = 0.0`
4. `coverage_rate = 1.0`
5. `latency_p95_ms = 27434.2`

结论：
- Live 链路可调用，回答可返回（覆盖率 100%）。
- 质量未达标（拒答、应急、常规问答均明显不足，时延偏高）。

## 本次代码修复
1. `skills/web-content-fetcher/scripts/fetch_web_content.py`
- 修复 malformed HTML entity 导致的解析崩溃。
- 加入解析器降级链路（`html.parser -> lxml -> html5lib -> 纯文本`）。

2. `scripts/eval_smoke.py`
- 支持 Dify `text/event-stream` 流式响应解析。
- 支持从 `message` 事件累计答案。
- 支持捕获 `workflow_finished.error`，避免误报为超时或空回答。

## 下一步建议（紧接当前结果）
1. 先修 Dify 工作流提示词与知识检索变量绑定（减少泛化回复）。
2. 重点修 20 题中失败最多的 10 题（按 `detailed_results.csv` 分簇）。
3. 修后立即重跑 `--limit 20` 回归，观察三项核心质量指标是否提升。

## 本次新增自动化补充（同日）

1. 新增失败分簇脚本：`scripts/analyze_eval_failures.py`
2. 回归流水线已默认追加输出：
- `eval_failure_clusters.csv`
- `eval_failure_clusters.md`
- `eval_top10_fix_list.csv`
3. 补充修复手册：
- `docs/eval/v4_2_dify绑定与Top10修复手册_20260328.md`
