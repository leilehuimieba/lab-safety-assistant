# 3轮稳定性验收证据（固化）

- 固化时间：`2026-03-30T22:58:53+08:00`
- 证据运行 ID：`run_20260330_211019`
- 结论：`PASS`

| Round | Status | Emergency | QA | Coverage | Latency P95(ms) | Route Success | Route Timeout | Failover | DemoPolicyExit | ProdPolicyExit |
|---|---|---:|---:|---:|---:|---:|---:|---|---:|---:|
| 1 | success | 1.0000 | 0.9091 | 1.0000 | 15981.76 | 1.0000 | 0.0000 | pass | 0 | 1 |
| 2 | success | 1.0000 | 0.9091 | 1.0000 | 27010.00 | 1.0000 | 0.0000 | pass | 0 | 1 |
| 3 | success | 1.0000 | 1.0000 | 1.0000 | 30981.91 | 1.0000 | 0.0000 | pass | 0 | 1 |

## 证据来源
- `artifacts/stability_evidence/run_20260330_211019/round_01_report.json`
- `artifacts/stability_evidence/run_20260330_211019/round_02_report.json`
- `artifacts/stability_evidence/run_20260330_211019/round_03_report.json`

## 说明
1. 本文件用于冻结三轮连续通过证据，避免后续单轮刷新覆盖。
2. 后续建议每次重大上线窗口都产出一份同类固化报告。
