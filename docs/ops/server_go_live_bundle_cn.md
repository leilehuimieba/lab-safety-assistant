# 服务器一键落地验收（Go-Live Bundle）

## 目标

将上线前关键动作串成一次命令执行，输出统一验收结果：

1. Provider 修复与真实工作流冒烟。
2. Embedding 通道自动修复（`host.docker.internal:11434`）。
3. 多轮稳定性验收（不跳过 failover eval）。
4. Go-live 预检（包完整性 + Web 健康 + 最新 one-click 结果）。

## 脚本与模板

- 执行脚本：`deploy/run_server_go_live_bundle.sh`
- 环境模板：`deploy/env/go_live_bundle.example.env`
- 输出结果：
  - `docs/ops/go_live_bundle_latest.json`
  - `docs/ops/go_live_bundle_latest.md`
  - `artifacts/go_live_bundle/run_*/`

## 使用步骤

```bash
cd /root/lab-safe-assistant-github
cp deploy/env/go_live_bundle.example.env deploy/env/go_live_bundle.env
vi deploy/env/go_live_bundle.env
chmod +x deploy/run_server_go_live_bundle.sh
./deploy/run_server_go_live_bundle.sh deploy/env/go_live_bundle.env
```

## 必填项

- `DIFY_TENANT_ID`
- `DIFY_APP_TOKEN`
- `DIFY_ENDPOINT_URL`
- `OPENAI_COMPAT_API_KEY`
- `DIFY_WORKFLOW_ID`

说明：`DIFY_WORKFLOW_ID` 是为了稳定性阶段强制走真实 failover 验收链路。

建议：`AUTO_FIX_EMBEDDING_CHANNEL=1` 保持开启，自动修复 embedding 健康检查失败。
建议：`DIFY_SMOKE_RETRIES=3`，降低上游偶发抖动导致的误失败。
建议：若 fallback 模型出现鉴权/超时不稳定，先将 `DIFY_FALLBACK_MODEL` 设为与主模型一致，先保证门禁可持续通过。

## 通过标准

`docs/ops/go_live_bundle_latest.json` 中：

- `overall = PASS`
- `steps.provider_recovery_and_smoke.ok = true`
- `steps.embedding_channel_ensure.ok = true`
- `steps.go_live_preflight.overall = PASS`
- `steps.release_stability_check.overall = PASS`

## 失败时优先排查

1. Provider 失败：先看 `artifacts/go_live_bundle/run_*/01_provider_recovery.log`
2. 预检失败：看 `docs/ops/go_live_readiness.md`
3. 稳定性失败：看 `docs/eval/release_stability_check.md` 和 `artifacts/release_stability_check/run_*/`

## 建议

- 首次迁移可先用 `STABILITY_ROUNDS=1` 快速验通。
- 正式发布前改回 `STABILITY_ROUNDS=3` 获取连续 PASS 证据。
