# Dify Chat SSE 阻塞记录（2026-03-28）

## 现象

- `POST /v1/chat-messages` 返回 `200`，`Content-Type: text/event-stream`。
- 客户端只能收到：
  - `event: ping`
  - 空行
- 后续长期无 `data:` 事件，最终在客户端超时。

## 已确认事实

- Celery worker 内部任务可以在数秒到十几秒内成功结束（日志可见 `workflow_based_app_execution_task ... succeeded`）。
- 但 API 流式响应没有把有效内容下发到调用方，导致 `eval_smoke` 全部 `request_error: timed out`。
- 该问题在主机侧 `http://localhost:8080` 与容器内直连 `http://api:5001` 都可复现。

## 影响

- `run_eval_regression_pipeline` 的 live smoke 结果出现全量 `primary_failed`。
- `route_success_rate` 连续周指标无法恢复，质量门禁持续失败。

## 临时措施

- 回归脚本增加 `--dify-response-mode` 参数，便于在不同模式间切换排障。
- 增加 `--skip-chat-preflight`，避免预检阻断整个流水线。
- 新增工作流应急脚本：
  - `scripts/patch_workflow_retrieval.py`（禁用/恢复检索）
  - `scripts/patch_workflow_model.py`（切换 LLM 模型）

## 下一步建议（优先级从高到低）

1. 在 Dify Web 界面新建一个最小化 App（`start -> llm -> answer`），仅做 `ok` 输出，验证是否仍只有 ping。
2. 若最小化 App 仍异常，重点排查 Dify API/网关流式转发配置，而不是工作流内容。
3. 若最小化 App 正常，再回到当前 App 逐步恢复节点（先 LLM，再知识检索），定位是哪类节点触发了 SSE 阻塞。
