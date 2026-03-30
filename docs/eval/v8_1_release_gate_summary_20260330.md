# v8.1 发布门禁与数据包结果（2026-03-30）

## 1) 可发布门禁结果

- 执行命令：
  - `python scripts/run_eval_release_oneclick.py --repo-root . --skip-failover-eval --release-policy-profile demo --release-policy-run-secondary --release-policy-secondary-profile prod --release-policy-enforce-secondary --release-policy-strict --output-root artifacts/eval_release_oneclick`
- 结论：`BLOCK`
- 关键原因（demo）：
  - `metric emergency_pass_rate too low: 0.0000 < min=0.8000`
  - `metric coverage_rate too low: 0.0000 < min=0.7500`
- 对应文件：
  - `docs/eval/release_policy_check.json`
  - `docs/eval/release_policy_check.md`
  - `docs/eval/release_risk_note_auto.json`
  - `docs/eval/release_risk_note_auto.md`

## 2) v8.1 可用数据包结果

- 抓取模式：`skill (jina,scrapling,direct)`
- 预抓取结果：`ok=18 / total=30`，`blocked=12`
- 低质量条目（改写前）：`26`
- 改写条目：`14/18`
- 导入包总条数：`368`

## 3) 交付物路径

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

## 4) 备注

- 当前无法进行 live Dify 回归（`http://localhost:8080` 连接被拒绝），因此门禁结论基于现有风险快照生成。
- 当 Dify 恢复后，建议优先重跑：
  - `powershell -File scripts/run_v7_dify_demo_chain.ps1 -SkipImport -EvalLimit 20`
