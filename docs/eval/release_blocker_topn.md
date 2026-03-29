# Release Blocker TopN

- Generated: `2026-03-29T16:02:06+08:00`

| Rank | Priority | Count | Profiles | Reason | Recommended Action |
|---:|---|---:|---|---|---|
| 1 | P2 | 1 | prod | gate_decision not allowed: WARN_ONLY not in ['PASS', 'WARN'] | 按违规描述逐项修复后，重跑一键发布校验链路。 |
| 2 | P2 | 1 | prod | risk violation count exceeded: 2 > max_violation_count=0 | 按违规描述逐项修复后，重跑一键发布校验链路。 |
| 3 | P1 | 1 | prod | override mode not allowed for profile prod: warn_only not in [] | 关闭临时豁免或切换到允许的发布 profile 后再执行发布。 |
| 4 | P0 | 1 | prod | route_success_rate too low: 0.0000 < min_route_success_rate=0.8000 | 优先修复主链路可用性，检查 Dify 网关/模型路由和网络连通性。 |
| 5 | P0 | 1 | prod | route_timeout_rate too high: 1.0000 > max_route_timeout_rate=0.2000 | 先降并发并排查 SSE 超时链路，必要时启用备用通道并重跑 canary。 |
| 6 | P1 | 1 | prod | latency_p95_ms too high: 60139.45 > max_latency_p95_ms=30000.00 | 优化提示词和检索链路，降低响应时延或调整限流策略。 |
| 7 | P0 | 1 | prod | failover latest result not allowed: fail not in ['degraded', 'pass'] | 定位主模型不可用原因，恢复后连续两轮回归验证再解除阻断。 |
| 8 | P0 | 1 | prod | failover latest timeout ratio too high: 1.0000 > max_latest_timeout_error_ratio=0.4000 | 提高请求稳定性（超时阈值、重试策略、模型通道），避免连续超时触发回退。 |
| 9 | P0 | 1 | prod | failover window fail count exceeded: 9 > max_fail_window=1 | 按违规描述逐项修复后，重跑一键发布校验链路。 |
| 10 | P0 | 1 | prod | failover fail streak exceeded: 9 > max_fail_streak=1 | 定位主模型不可用原因，恢复后连续两轮回归验证再解除阻断。 |
