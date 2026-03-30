# Release Blocker TopN

- Generated: `2026-03-30T09:44:38+08:00`

| Rank | Priority | Count | Profiles | Reason | Recommended Action |
|---:|---|---:|---|---|---|
| 1 | P2 | 1 | demo | metric emergency_pass_rate too low: 0.0000 < min=0.8000 | Fix listed blockers and rerun one-click release validation. |
| 2 | P2 | 1 | demo | metric coverage_rate too low: 0.0000 < min=0.7500 | Fix listed blockers and rerun one-click release validation. |
| 3 | P2 | 1 | prod | gate_decision not allowed: WARN_ONLY not in ['PASS', 'WARN'] | Fix listed blockers and rerun one-click release validation. |
| 4 | P2 | 1 | prod | risk violation count exceeded: 2 > max_violation_count=0 | Fix listed blockers and rerun one-click release validation. |
| 5 | P1 | 1 | prod | override mode not allowed for profile prod: warn_only not in [] | Disable temporary override or switch to an allowed release profile before release. |
| 6 | P0 | 1 | prod | route_success_rate too low: 0.0000 < min_route_success_rate=0.8000 | Recover primary route availability first; check Dify gateway, model routing, and network path. |
| 7 | P0 | 1 | prod | route_timeout_rate too high: 1.0000 > max_route_timeout_rate=0.2000 | Reduce concurrency and investigate SSE timeout path; enable fallback channel and rerun canary. |
| 8 | P1 | 1 | prod | latency_p95_ms too high: 60139.45 > max_latency_p95_ms=30000.00 | Optimize prompt and retrieval path, reduce latency, and tune rate limits. |
| 9 | P2 | 1 | prod | metric emergency_pass_rate too low: 0.0000 < min=0.9000 | Fix listed blockers and rerun one-click release validation. |
| 10 | P2 | 1 | prod | metric coverage_rate too low: 0.0000 < min=0.8500 | Fix listed blockers and rerun one-click release validation. |
