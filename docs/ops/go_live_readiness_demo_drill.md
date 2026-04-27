# Go-Live Readiness

- Generated: `2026-03-30T22:59:32+08:00`
- Overall: `PASS`
- Blockers: `0`
- Warnings: `0`

## Blockers
- none

## Warnings
- none

## Info
- [release_package::knowledge_base_import_ready.csv] ok
- [release_package::README.md] ok
- [release_package::web_seed_urls_v8_1_prefetch_status.csv] ok
- [release_oneclick] latest status=success (/root/lab-safe-assistant-github/artifacts/release_stability_check/run_20260330_220716/round_01/run_20260330_220716/eval_release_oneclick_report.json)
- [release_policy_demo] status=PASS
- [release_policy_prod] status=BLOCK; violations=latency_p95_ms too high: 30981.91 > max_latency_p95_ms=30000.00; failover window fail count exceeded: 4 > max_fail_window=1; non-blocking (enforce_prod_policy=false)
- [risk_note] gate_decision=PASS; emergency_pass_rate=1.0000
- [gate_override] override enabled=false
- [web_health] http://127.0.0.1:8088/health ok

## Next Actions
1. Ready for release window.
