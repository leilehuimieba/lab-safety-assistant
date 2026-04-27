# Go-Live 门禁演练（demo vs prod）

- 生成时间：`2026-03-30T22:59:32+08:00`
- 演练目标：对比 `GO_LIVE_ENFORCE_PROD_POLICY=0/1` 下的发布门禁行为差异。

| Mode | Overall | Blockers | release_policy_prod 结果 |
|---|---|---:|---|
| demo（不强制 prod） | PASS | 0 | status=BLOCK; violations=latency_p95_ms too high: 30981.91 > max_latency_p95_ms=30000.00; failover window fail count exceeded: 4 > max_fail_window=1; non-blocking (enforce_prod_policy=false) |
| prod（强制 prod） | BLOCK | 1 | status=BLOCK; violations=latency_p95_ms too high: 30981.91 > max_latency_p95_ms=30000.00; failover window fail count exceeded: 4 > max_fail_window=1 |

## 结论
1. 开启 `GO_LIVE_ENFORCE_PROD_POLICY=1` 后，门禁判定由 PASS 变为 BLOCK。
2. demo 模式适用于试运行与演示；正式发布窗口应开启 prod 强制门禁。
