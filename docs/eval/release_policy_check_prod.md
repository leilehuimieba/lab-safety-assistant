# Release Policy Check

- Generated: `2026-03-29T16:24:42+08:00`
- Profile: `prod`
- Status: `BLOCK`
- Strict: `True`

## Snapshot
- gate_decision: `WARN_ONLY`
- risk violations: `2`
- risk warnings: `0`
- override: `active=True, mode=warn_only`

## Violations
- gate_decision not allowed: WARN_ONLY not in ['PASS', 'WARN']
- risk violation count exceeded: 2 > max_violation_count=0
- override mode not allowed for profile prod: warn_only not in []
- route_success_rate too low: 0.0000 < min_route_success_rate=0.8000
- route_timeout_rate too high: 1.0000 > max_route_timeout_rate=0.2000
- latency_p95_ms too high: 60139.45 > max_latency_p95_ms=30000.00
- failover latest result not allowed: fail not in ['degraded', 'pass']
- failover latest timeout ratio too high: 1.0000 > max_latest_timeout_error_ratio=0.4000
- failover window fail count exceeded: 9 > max_fail_window=1
- failover fail streak exceeded: 9 > max_fail_streak=1

## Warnings
- none

## Files
- policy: `D:\workspace\lab-safe-assistant-github\docs\eval\release_policy_v5.json`
- risk note: `D:\workspace\lab-safe-assistant-github\docs\eval\release_risk_note_auto.json`
- failover status: `D:\workspace\lab-safe-assistant-github\docs\eval\failover_status.json`
- output json: `D:\workspace\lab-safe-assistant-github\docs\eval\release_policy_check_prod.json`
