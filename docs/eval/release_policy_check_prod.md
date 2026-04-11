# Release Policy Check

- Generated: `2026-04-11T03:51:32+00:00`
- Profile: `prod`
- Status: `BLOCK`
- Strict: `True`

## Snapshot
- gate_decision: `BLOCK`
- risk violations: `1`
- risk warnings: `0`
- override: `active=False, mode=warn_only`

## Violations
- gate_decision not allowed: BLOCK not in ['PASS', 'WARN']
- risk violation count exceeded: 1 > max_violation_count=0
- route_success_rate too low: 0.0000 < min_route_success_rate=0.8000
- metric missing/invalid in latest_metrics: emergency_pass_rate
- metric missing/invalid in latest_metrics: coverage_rate
- metric missing/invalid in latest_metrics: qa_pass_rate

## Warnings
- none

## Files
- policy: `/home/runner/work/lab-safety-assistant/lab-safety-assistant/docs/eval/release_policy_v5.json`
- risk note: `/home/runner/work/lab-safety-assistant/lab-safety-assistant/docs/eval/release_risk_note_auto.json`
- failover status: `/home/runner/work/lab-safety-assistant/lab-safety-assistant/docs/eval/failover_status.json`
- output json: `/home/runner/work/lab-safety-assistant/lab-safety-assistant/docs/eval/release_policy_check_prod.json`
