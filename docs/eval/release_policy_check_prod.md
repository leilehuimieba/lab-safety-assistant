# Release Policy Check

- Generated: `2026-03-30T10:06:00+08:00`
- Profile: `prod`
- Status: `BLOCK`
- Strict: `True`

## Snapshot
- gate_decision: `WARN_ONLY`
- risk violations: `1`
- risk warnings: `0`
- override: `active=True, mode=warn_only`

## Violations
- gate_decision not allowed: WARN_ONLY not in ['PASS', 'WARN']
- risk violation count exceeded: 1 > max_violation_count=0
- override mode not allowed for profile prod: warn_only not in []
- metric emergency_pass_rate too low: 0.8000 < min=0.9000

## Warnings
- none

## Files
- policy: `D:\workspace\lab-safe-assistant-github\docs\eval\release_policy_v5.json`
- risk note: `D:\workspace\lab-safe-assistant-github\docs\eval\release_risk_note_auto.json`
- failover status: `D:\workspace\lab-safe-assistant-github\docs\eval\failover_status.json`
- output json: `D:\workspace\lab-safe-assistant-github\docs\eval\release_policy_check_prod.json`
