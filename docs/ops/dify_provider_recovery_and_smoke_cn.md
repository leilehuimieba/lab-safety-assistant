# Dify Provider 恢复与真实验收（新服务器）

## 目的

当服务器迁移后出现以下问题时，用本流程一键修复并验收：

- `Provider ... does not exist`
- `Private key not found, tenant_id=...`
- 工作流调用失败，或 LLM 节点无输出

本流程会自动完成：

1. 重建租户私钥并更新公钥。
2. 重写 `openai_api_compatible` 的 provider/model 凭据（API Key 重新加密）。
3. 触发一轮真实工作流调用，检查 `workflow_finished.status` 与可读答案。

## 脚本位置

- 主脚本：`scripts/release/recover_dify_provider_and_smoke.py`
- 一键入口：`scripts/run_dify_provider_recovery_and_smoke.sh`
- 环境模板：`deploy/env/dify_provider_recovery.example.env`

## 快速开始（服务器）

假设仓库目录为 `/root/lab-safe-assistant-github`：

```bash
cd /root/lab-safe-assistant-github
cp deploy/env/dify_provider_recovery.example.env deploy/env/dify_provider_recovery.env
vi deploy/env/dify_provider_recovery.env
```

至少填写这 4 个字段：

- `DIFY_TENANT_ID`
- `DIFY_APP_TOKEN`
- `DIFY_ENDPOINT_URL`
- `OPENAI_COMPAT_API_KEY`

可选增强（建议）：

- `DIFY_SMOKE_RETRIES=3`
- `DIFY_SMOKE_RETRY_INTERVAL_SEC=3`
- `DIFY_FORCE_ROTATE_KEY=0`（默认不轮转密钥，仅缺失时补齐）

执行：

```bash
chmod +x scripts/run_dify_provider_recovery_and_smoke.sh
./scripts/run_dify_provider_recovery_and_smoke.sh deploy/env/dify_provider_recovery.env
```

## 通过标准

命令返回码为 `0`，并且输出中满足：

- `workflow_finished.status` 为 `succeeded` 或 `success`
- `answer_preview` 非空且可读

注意：Dify 某些版本使用 `succeeded`，语义等同 `success`。

## 常见失败与处理

1. `docker ps` 找不到 API 容器  
处理：在 env 中设置 `DIFY_API_CONTAINER=docker-api-1`（按实际容器名）。

2. `tenant not found`  
处理：检查 `DIFY_TENANT_ID` 是否来自当前 Dify 实例，而不是旧服务器。

3. `http 401/403`  
处理：检查 `DIFY_APP_TOKEN` 是否是该应用有效 token。

4. 工作流超时  
处理：提高 `DIFY_SMOKE_TIMEOUT_SEC`，同时检查中转 API 可达性。

## 安全建议

- 不要把真实 `OPENAI_COMPAT_API_KEY` 提交到 Git。
- `deploy/env/*.env` 建议仅保留在服务器，仓库只提交 `example.env`。
