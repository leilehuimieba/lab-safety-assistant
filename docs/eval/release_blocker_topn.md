# Release Blocker TopN

- Generated: `2026-04-11T03:51:32+00:00`

| Rank | Priority | Count | Profiles | Reason | Recommended Action |
|---:|---|---:|---|---|---|
| 1 | P2 | 2 | demo,prod | metric missing/invalid in latest_metrics: emergency_pass_rate | Fix listed blockers and rerun one-click release validation. |
| 2 | P2 | 2 | demo,prod | metric missing/invalid in latest_metrics: coverage_rate | Fix listed blockers and rerun one-click release validation. |
| 3 | P2 | 1 | demo | gate_decision not allowed: BLOCK not in ['PASS', 'WARN', 'WARN_ONLY'] | Fix listed blockers and rerun one-click release validation. |
| 4 | P2 | 1 | prod | gate_decision not allowed: BLOCK not in ['PASS', 'WARN'] | Fix listed blockers and rerun one-click release validation. |
| 5 | P2 | 1 | prod | risk violation count exceeded: 1 > max_violation_count=0 | Fix listed blockers and rerun one-click release validation. |
| 6 | P0 | 1 | prod | route_success_rate too low: 0.0000 < min_route_success_rate=0.8000 | Recover primary route availability first; check Dify gateway, model routing, and network path. |
| 7 | P2 | 1 | prod | metric missing/invalid in latest_metrics: qa_pass_rate | Fix listed blockers and rerun one-click release validation. |
