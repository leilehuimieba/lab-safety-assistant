# Release Fix Plan (Auto)

- Generated: `2026-03-30T09:25:54+08:00`
- Total Tasks: `10`
- todo: `10`
- in_progress: `0`
- blocked: `0`
- done: `0`

| Task ID | Priority | Status | Owner | ETA | Profiles | Blocking Reason | Recommended Action | Verification Step |
|---|---|---|---|---|---|---|---|---|
| REL-FIX-11 | P2 | todo |  |  | demo | metric emergency_pass_rate too low: 0.0000 < min=0.8000 | Fix listed blockers and rerun one-click release validation. | Re-run one-click release check and verify profile status is PASS. |
| REL-FIX-12 | P2 | todo |  |  | demo | metric coverage_rate too low: 0.0000 < min=0.7500 | Fix listed blockers and rerun one-click release validation. | Re-run one-click release check and verify profile status is PASS. |
| REL-FIX-13 | P2 | todo |  |  | prod | gate_decision not allowed: WARN_ONLY not in ['PASS', 'WARN'] | Fix listed blockers and rerun one-click release validation. | Re-run one-click release check and verify profile status is PASS. |
| REL-FIX-14 | P2 | todo |  |  | prod | risk violation count exceeded: 2 > max_violation_count=0 | Fix listed blockers and rerun one-click release validation. | Re-run one-click release check and verify profile status is PASS. |
| REL-FIX-15 | P1 | todo |  |  | prod | override mode not allowed for profile prod: warn_only not in [] | Disable temporary override or switch to an allowed release profile before release. | Re-run one-click release check and verify profile status is PASS. |
| REL-FIX-16 | P0 | todo |  |  | prod | route_success_rate too low: 0.0000 < min_route_success_rate=0.8000 | Recover primary route availability first; check Dify gateway, model routing, and network path. | Re-run one-click release check and verify profile status is PASS. |
| REL-FIX-17 | P0 | todo |  |  | prod | route_timeout_rate too high: 1.0000 > max_route_timeout_rate=0.2000 | Reduce concurrency and investigate SSE timeout path; enable fallback channel and rerun canary. | Re-run one-click release check and verify profile status is PASS. |
| REL-FIX-18 | P1 | todo |  |  | prod | latency_p95_ms too high: 60139.45 > max_latency_p95_ms=30000.00 | Optimize prompt and retrieval path, reduce latency, and tune rate limits. | Re-run one-click release check and verify profile status is PASS. |
| REL-FIX-19 | P2 | todo |  |  | prod | metric emergency_pass_rate too low: 0.0000 < min=0.9000 | Fix listed blockers and rerun one-click release validation. | Re-run one-click release check and verify profile status is PASS. |
| REL-FIX-20 | P2 | todo |  |  | prod | metric coverage_rate too low: 0.0000 < min=0.8500 | Fix listed blockers and rerun one-click release validation. | Re-run one-click release check and verify profile status is PASS. |
