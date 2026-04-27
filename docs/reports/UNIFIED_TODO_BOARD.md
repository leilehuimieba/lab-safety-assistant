# 唯一待办总表（Unified Todo Board）

- 更新时间：`2026-04-26 23:44`
- 适用范围：`lab-safety-assistant-remote` 当前仓库
- 维护规则：从现在开始，推进状态只在本表更新；其他文档作为证据来源，不再各自维护待办状态。

## 状态定义

| 状态 | 含义 |
|---|---|
| todo | 尚未开始 |
| in_progress | 正在执行 |
| blocked | 受外部条件阻塞 |
| done | 已完成并通过验证 |

## 统一待办（按优先级）

| Task ID | Priority | 状态 | Owner | 任务 | 完成判据 | 验证命令 |
|---|---|---|---|---|---|---|
| REL-FIX-16 | P0 | done | 平台维护（主）/ 发布与验收负责人（验收） | 恢复主链路可用，`route_success_rate >= 0.80` | `docs/eval/release_policy_check_prod.json` 为 `PASS`，且阻断原因不再出现 `route_success_rate too low` | CMD-REL-01, CMD-REL-02, CMD-REL-03 |
| REL-FIX-17 | P0 | done | 平台维护（主）/ 发布与验收负责人（验收） | 将超时率压到阈值内，`route_timeout_rate <= 0.20` | `release_fix_plan_auto.md/csv` 中不再出现 `route_timeout_rate too high` | CMD-REL-01, CMD-REL-02, CMD-REL-05 |
| GO-LIVE-HEALTH-01 | P0 | done | 平台维护（主）/ 发布与验收负责人（验收） | 修复 `/health` 不可达（10061）问题 | `docs/ops/go_live_readiness.md` 不再包含 `web_health unreachable`，整体不是因健康检查而 `BLOCK` | CMD-GO-01, CMD-GO-02 |
| REL-FIX-15 | P1 | done | 发布与验收负责人 | 关闭 `prod` 的临时 override（`warn_only`） | 已完成：`release_fix_plan_auto.md` 显示 `Total Tasks: 0`，且 override active=False | CMD-REL-01, CMD-REL-02 |
| REL-FIX-18 | P1 | done | 平台维护（主）/ 发布与验收负责人（验收） | 压低延迟，`latency_p95_ms <= 30000` | `prod` 策略不再出现 `latency_p95_ms too high`；稳定性报告可追溯 | CMD-REL-01, CMD-STAB-01, CMD-REL-03 |
| DATA-LOWQ-V82-01 | P1 | done | 数据清洗员（主）/ 发布与验收负责人（验收） | 清洗 `v8.2` 的 3 条低质量来源（WEB82-024/026/027） | 已完成：`docs/pipeline/web_seed_v8_2_prefetch_report.md` 中 low quality 已降为 `0` | CMD-DATA-01, CMD-DATA-02 |
| DOC-SYNC-01 | P1 | done | 发布与验收负责人 | 统一 go-live 口径（`go_live_readiness` 与 `go_live_failure_digest` 同轮次） | 两份文档由同一轮预检生成，结论一致且可追溯 | CMD-GO-01, CMD-GO-03 |
| REL-FIX-11 | P2 | done | 发布与验收负责人 | 修复 `demo emergency_pass_rate` 阈值不达标 | 已完成：demo policy PASS，且 `release_fix_plan_auto.md` 显示 `Total Tasks: 0` | CMD-REL-01, CMD-REL-02 |
| REL-FIX-12 | P2 | done | 发布与验收负责人 | 修复 `demo coverage_rate` 阈值不达标 | 已完成：demo readiness PASS，且 `release_fix_plan_auto.md` 显示 `Total Tasks: 0` | CMD-REL-01, CMD-REL-02 |
| REL-FIX-13 | P2 | done | 发布与验收负责人 | 修复 `prod gate_decision` 不在允许值（`WARN_ONLY`） | 已完成：prod gate_decision=PASS，且 `release_fix_plan_auto.md` 显示 `Total Tasks: 0` | CMD-REL-01, CMD-REL-02, CMD-REL-03 |
| REL-FIX-14 | P2 | done | 发布与验收负责人 | 修复 `prod risk violation count` 超阈值 | 已完成：prod risk violations=0，且 `release_fix_plan_auto.md` 显示 `Total Tasks: 0` | CMD-REL-01, CMD-REL-02, CMD-REL-03 |
| REL-FIX-19 | P2 | done | 发布与验收负责人 | 修复 `prod emergency_pass_rate` 阈值不达标 | `release_fix_plan_auto` 不再出现 `REL-FIX-19` 阻断原因 | CMD-REL-01, CMD-REL-02, CMD-REL-03 |
| REL-FIX-20 | P2 | done | 发布与验收负责人 | 修复 `prod coverage_rate` 阈值不达标 | 已完成：prod readiness PASS，且 `release_fix_plan_auto.md` 显示 `Total Tasks: 0` | CMD-REL-01, CMD-REL-02, CMD-REL-03 |
| DOC-ARCH-01 | P2 | todo | 发布与验收负责人 | 补 `docs/README.md` 作为文档执行入口（避免状态分散） | `docs/README.md` 存在且指向本表为唯一待办入口 | CMD-DOC-01 |

## 本轮成功 Run 证据（2026-04-26）

| Task ID | 证据路径 |
|---|---|
| REL-FIX-16 | `artifacts/eval_release_oneclick/run_20260426_225546/eval_release_oneclick_report.json`（`route_success_rate=1.0`） |
| REL-FIX-17 | `artifacts/eval_release_oneclick/run_20260426_225546/eval_release_oneclick_report.json`（`route_timeout_rate=0.0`） |
| GO-LIVE-HEALTH-01 | `docs/ops/go_live_readiness.md`（`Overall: PASS` 且 `web_health ... ok`） |
| REL-FIX-18 | `docs/eval/release_policy_check_prod.json`（`status=PASS` 且无 `latency_p95_ms too high`） |
| REL-FIX-19 | `artifacts/eval_release_oneclick/run_20260426_225546/eval_release_oneclick_report.json`（`emergency_pass_rate=1.0`） |
| CMD-STAB-01（3轮稳定性） | `docs/eval/release_stability_check.json`（`overall=PASS, passed_rounds=3/3`） |
| DOC-SYNC-01 | `docs/ops/go_live_readiness.md` + `docs/ops/go_live_failure_digest_latest.md`（同轮均为 `PASS`） |
| 本轮总体验收 | `docs/eval/release_policy_check.json`、`docs/eval/release_policy_check_prod.json`、`docs/ops/release_fix_plan_auto.md`（`Total Tasks: 0`） |

## 命令清单（复制即用）

### CMD-REL-01：一键回归链路（含发布策略）

```powershell
set DIFY_BASE_URL=http://localhost:8080
set DIFY_APP_API_KEY=<app-xxxx>
python scripts/run_eval_release_oneclick.py `
  --repo-root . `
  --workflow-id <workflow_id> `
  --primary-model gpt-5.2-codex `
  --fallback-model MiniMax-M2.5 `
  --health-allow-chat-timeout-pass `
  --canary-limit 3 `
  --canary-timeout 20 `
  --canary-retry-on-timeout 0 `
  --limit 20 `
  --dify-timeout 60 `
  --eval-concurrency 1 `
  --retry-on-timeout 1 `
  --failover-fail-streak-threshold 2 `
  --release-policy-profile prod `
  --release-policy-run-secondary `
  --release-policy-secondary-profile prod `
  --release-policy-enforce-secondary `
  --release-policy-strict
```

### CMD-REL-02：刷新发布就绪看板与修复计划

```powershell
python scripts/generate_release_readiness_dashboard.py `
  --repo-root . `
  --profiles demo,prod `
  --strict-profiles demo,prod
```

### CMD-REL-03：单独验证 prod 发布策略

```powershell
python scripts/validate_release_policy.py `
  --repo-root . `
  --profile prod `
  --strict
```

### CMD-REL-05：修复计划质量门校验

```powershell
python scripts/validate_release_fix_plan.py --repo-root .
```

### CMD-GO-01：go-live 预检（Windows）

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_go_live_preflight.ps1 `
  -RepoRoot . `
  -ReleaseDir release_exports/v8.2 `
  -WebHealthUrl http://127.0.0.1:8088/health
```

### CMD-GO-02：服务器侧启动演示服务并预检（Linux）

```bash
./deploy/start_web_demo.sh
./deploy/go_live_preflight.sh
```

### CMD-GO-03：生成 go-live failure digest（同步口径）

```powershell
python scripts/release/generate_go_live_failure_digest.py --repo-root .
```

### CMD-STAB-01：连续稳定性验收（3轮）

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_release_stability_check.ps1 `
  -RepoRoot . `
  -Rounds 3 `
  -IntervalSec 30 `
  -WorkflowId <workflow_id> `
  -DifyBaseUrl http://localhost:8080 `
  -DifyAppKey <app_key> `
  -SkipHealthCheck `
  -SkipCanary
```

### CMD-DATA-01：低质量行重写（v8.2）

```powershell
python scripts/rewrite_low_quality_rows.py `
  --input-csv release_exports/v8.2/knowledge_base_web_v8_2.csv `
  --status-csv data_sources/web_seed_urls_v8_2_prefetch_status.csv `
  --output-csv release_exports/v8.2/knowledge_base_web_v8_2_rewritten.csv `
  --log-csv release_exports/v8.2/rewrite_log_v8_2.csv `
  --low-quality-threshold 0.70
```

### CMD-DATA-02：重生成 v8.2 预抓取报告

```powershell
python scripts/generate_web_prefetch_report.py `
  --status-csv data_sources/web_seed_urls_v8_2_prefetch_status.csv `
  --output-report docs/pipeline/web_seed_v8_2_prefetch_report.md `
  --output-assignment release_exports/v8.2/web_seed_v8_2_task_assignment.csv `
  --batch-name web_seed_v8_2
```

### CMD-DOC-01：文档入口自检

```powershell
if (Test-Path docs/README.md) { 'docs/README.md exists' } else { 'docs/README.md missing' }
```

## 证据来源

- `docs/ops/release_fix_plan_auto.md`
- `docs/ops/release_fix_plan_auto.csv`
- `docs/ops/go_live_readiness.md`
- `docs/ops/go_live_failure_digest_latest.md`
- `docs/eval/formal_acceptance_20260331.md`
- `docs/pipeline/web_seed_v8_2_prefetch_report.md`
- `docs/reports/PROJECT_STATUS.md`
