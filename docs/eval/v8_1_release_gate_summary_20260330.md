# v8.1 发布门禁与数据包结果（2026-03-30）

## 1) 可发布门禁结果

- 执行命令：
  - `python scripts/run_eval_release_oneclick.py --repo-root . --skip-failover-eval --release-policy-profile demo --release-policy-run-secondary --release-policy-secondary-profile prod --release-policy-enforce-secondary --release-policy-strict --output-root artifacts/eval_release_oneclick`
- 门禁结果：`blocked_by_release_policy_secondary`
- demo（strict）：`PASS`
- prod（strict）：`BLOCK`
- prod 阻断原因：
  - `gate_decision not allowed: WARN_ONLY not in ['PASS', 'WARN']`
  - `risk violation count exceeded: 1 > max_violation_count=0`
  - `override mode not allowed for profile prod: warn_only not in []`
  - `metric emergency_pass_rate too low: 0.8000 < min=0.9000`
- 对应文件：
  - `docs/eval/release_policy_check.json`
  - `docs/eval/release_policy_check.md`
  - `docs/eval/release_policy_check_prod.json`
  - `docs/eval/release_policy_check_prod.md`
  - `docs/eval/release_risk_note_auto.json`
  - `docs/eval/release_risk_note_auto.md`
  - `artifacts/eval_release_oneclick/run_20260330_100559/eval_release_oneclick_report.json`

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

- 当前“demo 发布门禁”已经可过，但“prod 发布门禁”仍阻断。
- 要让 prod 放行，最小改造是两项：
  - 生成有效的 failover latest 记录，消除 `WARN_ONLY` 风险违规。
  - 将最新评测 `emergency_pass_rate` 从 `0.8` 提升到 `>=0.9`。
