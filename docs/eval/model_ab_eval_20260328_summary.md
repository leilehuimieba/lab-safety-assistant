# 模型通道 A/B 实测总结（2026-03-28）

## 本轮任务

对同一工作流执行模型通道 A/B 对比，验证是否由“模型通道本身”导致回归长耗时与超时。

- A：`MiniMax-M2.5`
- B：`gpt-5.2-codex`
- 评测参数：`limit=6`、`dify-timeout=30s`、`eval-concurrency=4`

## 自动化脚本

- `scripts/run_model_ab_eval.py`

能力：

1. 自动备份当前 workflow graph（发布版 + draft）。
2. 自动切换模型名并跑回归。
3. 自动恢复原始 workflow 配置（防止污染线上配置）。
4. 输出 JSON + Markdown 对比报告。

## 结果结论

两组都出现了同样的超时表现：

- 覆盖率：`0.0%`
- 延迟 P95：约 `30s`（贴近请求超时阈值）
- `fetch_error` 主要为 `request_error: timed out`

结论：本轮主要瓶颈不在模型名切换，而在上游网关/模型服务响应稳定性。

## 产物路径

- `artifacts/model_ab_eval/run_20260328_122324/model_ab_report.md`
- `artifacts/model_ab_eval/run_20260328_122324/model_ab_report.json`

## 下一步建议（按优先级）

1. 优先做“上游健康检查与降级”：
   - 在回归前先检查网关是否可用（已接入 preflight）。
   - 增加备用通道（同 provider 第二凭据 / 本地模型直连）并在超时时自动降级。
2. 将 `dify-timeout` 保持在 `20~30s`，防止整轮评测耗时失控。
3. 上游稳定后，再回到“提示词/知识库命中”质量优化，否则质量评测会被超时噪声淹没。
