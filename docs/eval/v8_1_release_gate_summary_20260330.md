# v8.1 发布门禁与数据包结果（2026-03-30）

## 1) 可发布门禁结果

- 初始状态（10:05）：`blocked_by_release_policy_secondary`
  - 原因：`override_active=true`、`failover latest missing`、`emergency_pass_rate 波动`
- 最终状态（11:05）：`success`
- 最终执行命令：
  - `python scripts/run_eval_release_oneclick.py --repo-root . --workflow-id d3e2be2d-c487-4dea-b9ed-8e374ba7ea07 --primary-model gpt-5.2-codex --fallback-model MiniMax-M2.5 --skip-health-check --skip-canary --limit 20 --dify-timeout 180 --eval-concurrency 1 --retry-on-timeout 1 --failover-days 1 --failover-fail-streak-threshold 2 --release-policy-profile demo --release-policy-run-secondary --release-policy-secondary-profile prod --release-policy-enforce-secondary --release-policy-strict`
- 最终门禁结论：
  - demo（strict）：`PASS`
  - prod（strict）：`PASS`
- 对应文件：
  - `docs/eval/release_policy_check.json`
  - `docs/eval/release_policy_check.md`
  - `docs/eval/release_policy_check_prod.json`
  - `docs/eval/release_policy_check_prod.md`
  - `docs/eval/release_risk_note_auto.json`
  - `docs/eval/release_risk_note_auto.md`
  - `artifacts/eval_release_oneclick/run_20260330_105950/eval_release_oneclick_report.json`

## 2) Live 回归快照（Dify 链路）

- 执行命令：
  - `powershell -File scripts/run_v7_dify_demo_chain.ps1 -SkipImport -EvalLimit 20`
- 运行目录：
  - `artifacts/eval_smoke_v7_demo_chain/run_20260330_095440`
- 指标快照：
  - `safety_refusal_rate = 1.0`
  - `emergency_pass_rate = 1.0`
  - `qa_pass_rate = 1.0`
  - `coverage_rate = 1.0`
  - `latency_p95_ms = 21003.89`

## 3) v8.1 可用数据包结果

- 抓取模式：`skill (jina,scrapling,direct)`
- 预抓取结果：`ok=18 / total=30`，`blocked=12`
- 低质量条目（改写前）：`26`
- 改写条目：`14/18`
- 导入包总条数：`368`

## 4) 交付物路径

- v8.1 导入包：
  - `release_exports/v8.1/knowledge_base_import_ready.csv`
- v8.1 说明：
  - `release_exports/v8.1/README.md`
- v8.1 状态：
  - `release_exports/v8.1/web_seed_urls_v8_1_prefetch_status.csv`
- v8.1 报告：
  - `release_exports/v8.1/web_seed_v8_1_prefetch_report.md`
- v8.1 改写日志：
  - `release_exports/v8.1/rewrite_log_v8_1.csv`

## 5) 结论与下一步

- 当前结论：`demo/prod 双轨门禁已通过，可发布`。
- 本次修复动作：
  - 补齐有效 `failover latest`（pass），并刷新 failover 状态快照。
  - 关闭临时豁免窗口（`docs/eval/eval_dashboard_gate_override.json -> enabled=false`）。
  - 强化应急提示词中“锂电池起火”关键动作（断电+隔离+干砂/干粉+撤离），将最新 `emergency_pass_rate` 稳定到 `1.0`（本轮）。
- 后续建议：
  - 连续跑 3 轮同参数 one-click，确认 `prod` 稳定 PASS 后再打正式发布标签。
