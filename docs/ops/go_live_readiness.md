# Go-Live Readiness

> 历史路径说明：本文中的 `D:\workspace\...` 为生成本报告时的历史运行路径，仅用于证据追溯；当前默认工作区以 `D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github` 为准。
> 当前阅读规则：若本文中的历史证据路径与当前启动入口冲突，以 `docs/README.md`、`AGENTS.md` 和 `scripts/start_web_demo_local.ps1` 为准。

- Generated: `2026-04-08T23:26:04+08:00`
- Overall: `BLOCK`
- Blockers: `2`
- Warnings: `0`

## Blockers
- [release_policy_prod] status=BLOCK; violations=failover window fail count exceeded: 4 > max_fail_window=1
- [web_health] http://127.0.0.1:8088/health unreachable: <urlopen error [WinError 10061] 由于目标计算机积极拒绝，无法连接。>

## Warnings
- none

## Info
- [release_package::knowledge_base_import_ready.csv] ok
- [release_package::README.md] ok
- [release_package::web_seed_urls_v8_1_prefetch_status.csv] ok
- [release_oneclick] latest status=success (D:\workspace\lab-safe-assistant-github\artifacts\release_stability_check\run_20260330_114443\round_01\run_20260330_114443\eval_release_oneclick_report.json)
- [release_policy_demo] status=PASS
- [risk_note] gate_decision=PASS; emergency_pass_rate=1.0000
- [gate_override] override enabled=false

## Next Actions
1. Fix all blockers first, then rerun go-live preflight.
