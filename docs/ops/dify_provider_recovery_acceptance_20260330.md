# Dify Provider 恢复验收记录（2026-03-30）

## 目标

在新服务器完成以下目标：

1. `openai_api_compatible` provider 可正常使用中转 API。
2. 真实工作流调用返回 `workflow_finished.status=success/succeeded`。
3. 返回内容可读且非空。

## 环境

- 服务器：`175.178.90.193`
- 仓库目录：`/root/lab-safe-assistant-github`
- Dify API 容器：`docker-api-1`
- 租户：`7980ac46-b7f0-4f67-b94e-fbcc0bf48a46`
- 模型：`gpt-5.2-codex`

## 执行命令

```bash
cd /root/lab-safe-assistant-github
chmod +x scripts/run_dify_provider_recovery_and_smoke.sh
./scripts/run_dify_provider_recovery_and_smoke.sh deploy/env/dify_provider_recovery.env
```

## 验收结果

- `provider recovery result`：
  - `private_key_bytes = 1674`
  - provider/model 凭据均可更新并保持有效
- `workflow smoke result`：
  - `http_status = 200`
  - `workflow_finished.status = succeeded`
  - `workflow_run_id = 99e68051-e643-4509-be5d-8973adee6c56`
  - `answer_preview` 可读、非空

结论：通过。

## 备注

- Dify 某些版本状态字段为 `succeeded`，语义等同 `success`。
- 真实密钥与 token 未入库，仅保留 `deploy/env/dify_provider_recovery.example.env` 模板。
