# 超时复检根因报告（2026-03-30）

本轮针对以下失败条目做了自动复检：

- 来源：`artifacts/eval_smoke_v7_demo_chain_retry/run_20260329_201650/detailed_results.csv`
- 失败题目：`EVAL-0011`、`EVAL-0012`

复检命令：

```powershell
python scripts/retry_eval_timeouts.py `
  --input-detailed-results artifacts/eval_smoke_v7_demo_chain_retry/run_20260329_201650/detailed_results.csv `
  --dify-base-url http://localhost:8080 `
  --dify-app-key <app-key> `
  --output-dir artifacts/eval_timeout_retry
```

## 结果结论

- 复检批次：`artifacts/eval_timeout_retry/run_20260330_082907`
- 恢复数：`0/2`
- 根因分布：`endpoint_unreachable_or_service_down = 2`

即：当时并非仅仅“模型慢”，而是评测请求所在时刻出现了接口不可达（`WinError 10061`，端口拒绝连接）。

## 产物

- 复检总览：`artifacts/eval_timeout_retry/run_20260330_082907/timeout_retry_summary.json`
- 复检明细：`artifacts/eval_timeout_retry/run_20260330_082907/timeout_retry_attempts.csv`
- 案例汇总：`artifacts/eval_timeout_retry/run_20260330_082907/timeout_retry_case_summary.csv`

## 处置建议（高优先）

1. 在回归前固定执行 `check_live_eval_health.py`，未通过则直接阻断回归。
2. 保持 `eval_smoke` 评测并发为 `1`，先保证稳定再提速。
3. 导入后等待索引完成再回归，减少导入高峰期对响应时间的影响。
