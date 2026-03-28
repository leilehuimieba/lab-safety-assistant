# 回归链路降级能力上线说明（2026-03-28）

## 本次任务

为评测链路增加“主通道超时自动降级到备用通道”的能力，避免整轮评测因上游波动失真。

## 已实现能力

1. `eval_smoke.py` 新增参数：
- `--retry-on-timeout`
- `--fallback-dify-base-url`
- `--fallback-dify-app-key`

2. 响应新增路由字段：
- `response_route`（`primary` / `fallback` / `primary_failed` / `fallback_failed`）

3. `run_eval_regression_pipeline.py` 支持透传上述参数，直接一条命令启用降级。

## 建议用法

```powershell
set DIFY_BASE_URL=http://localhost:8080
set DIFY_APP_API_KEY=<app-primary>
set DIFY_FALLBACK_BASE_URL=http://localhost:8080
set DIFY_FALLBACK_APP_API_KEY=<app-backup>

python scripts/run_eval_regression_pipeline.py `
  --repo-root . `
  --limit 20 `
  --dify-timeout 20 `
  --eval-concurrency 4 `
  --retry-on-timeout 1 `
  --update-dashboard
```

## 本地验证结论

已执行 2 题验证，结果中出现 `response_route=fallback_failed`，说明主通道失败后已尝试备用通道并正确记录错误链路。

后续评估时可直接按 `response_route` 分析：

- 若 `primary_failed/fallback_failed` 高，优先处理上游可用性。
- 若 `primary/fallback` 覆盖率高但得分低，再做知识库与提示词优化。
