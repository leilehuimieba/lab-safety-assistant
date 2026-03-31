# 3轮稳定性验收证据（2026-03-31）

- 固化时间：`2026-03-31T22:20:00+08:00`
- 证据运行 ID：`run_20260331_211146`
- 结论：`PASS`

| Round | Status | Safety Refusal | Emergency | QA | Coverage | Latency P95(ms) | DemoPolicyExit | ProdPolicyExit |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | success | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 21202.63 | 0 | 0 |
| 2 | success | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 18193.32 | 0 | 0 |
| 3 | success | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 49532.83 | 0 | 1 |

## 证据来源

- `artifacts/release_stability_check_20260331_perf/run_20260331_211146/round_01/run_20260331_211146/eval_release_oneclick_report.json`
- `artifacts/release_stability_check_20260331_perf/run_20260331_211146/round_02/run_20260331_211708/eval_release_oneclick_report.json`
- `artifacts/release_stability_check_20260331_perf/run_20260331_211146/round_03/run_20260331_212135/eval_release_oneclick_report.json`

## 说明

1. 三轮真实回归的正确率指标全部稳定通过，说明 `20/20` 不是偶然结果。
2. Round 3 的 `ProdPolicyExit=1` 不是正确率问题，而是尾部延迟波动导致的生产门禁未完全收敛。
3. 因此当前对外口径应为：
   - 正确率：稳定达标
   - 演示/答辩：可用
   - 生产级性能：仍需继续优化

