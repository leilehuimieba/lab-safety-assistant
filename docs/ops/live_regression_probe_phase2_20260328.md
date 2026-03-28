# Live 回归二阶段排障记录（2026-03-28）

## 执行目标

验证“最小工作流 + 渐进恢复”的链路，定位是流程节点问题还是模型通道问题，并给出可执行参数基线。

## 执行过程

1. 将当前 workflow 临时改为最小链路：`start -> llm -> answer`（已自动备份）。
2. 对比两种响应模式：
- `blocking`：只收到 `event: ping`，随后超时。
- `streaming`：可收到 `workflow_started/message/...` 事件。
3. 恢复非最小流程并逐步回加：
- 恢复业务提示词与回答节点；
- 切换模型到 `gpt-5.2-codex`；
- 回加知识检索节点后短测仍可出结果（未再次出现“全量阻断”）。
4. 调整评测参数后复跑 live regression：
- `--dify-response-mode streaming`
- `--dify-timeout 60`
- `--eval-concurrency 1`

## 关键结论

1. 当前环境下，`blocking` 模式不稳定，`streaming` 更可用。
2. 评测超时阈值过低会导致误判；`60s` 明显优于 `30~40s`。
3. 路由层已恢复可用（单轮 `route_success_rate = 1.0` 可达），但历史失败 run 较多，周维度门禁值恢复较慢。

## 已落地代码改动

- `eval_smoke.py`
  - 新增 `--dify-response-mode`
  - SSE 读取加入“硬超时截止线”，避免 ping 导致无限等待
- `run_eval_regression_pipeline.py`
  - chat 预检支持按 response mode 校验
  - 默认 `dify-response-mode` 调整为 `streaming`
- 新增 workflow 工具脚本：
  - `scripts/patch_workflow_retrieval.py`
  - `scripts/patch_workflow_model.py`
  - `scripts/patch_workflow_minimal.py`

## 当前建议

1. 短期稳定参数固定为：
- `--dify-response-mode streaming`
- `--dify-timeout 60`
- `--eval-concurrency 1`
2. 每天跑 1~2 轮 live regression，逐步抬升周指标。
3. 若要立即解除“连续两周 route 门禁”阻断，建议临时启用 `warn_only` override（带审批记录）。
