# 服务器一键落地验收（Go-Live Bundle）

## 目标

将上线前关键动作串成一次命令执行，输出统一验收结果：

1. Provider 修复与真实工作流冒烟。  
2. Embedding 通道自动修复（`host.docker.internal:11434`）。  
3. 多轮稳定性验收（不跳过 failover eval）。  
4. Go-live 预检（包完整性 + Web 健康 + 最新 one-click 结果）。  

## 脚本与模板

- 执行脚本：`deploy/run_server_go_live_bundle.sh`
- 定时脚本：`deploy/install_go_live_bundle_cron.sh` / `deploy/status_go_live_bundle_cron.sh` / `deploy/uninstall_go_live_bundle_cron.sh`
- 环境模板：`deploy/env/go_live_bundle.example.env`
- 输出结果：
  - `docs/ops/go_live_bundle_latest.json`
  - `docs/ops/go_live_bundle_latest.md`
  - `docs/ops/go_live_failure_digest_latest.json`
  - `docs/ops/go_live_failure_digest_latest.md`
  - `docs/ops/runtime_profile_snapshot.json`
  - `docs/ops/runtime_profile_snapshot.md`
  - `artifacts/go_live_bundle/run_*/`

## 快速开始

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

## 推荐配置

- `AUTO_FIX_EMBEDDING_CHANNEL=1`：自动修复 embedding 通道。  
- `DIFY_SMOKE_RETRIES=3`：降低偶发抖动导致的误失败。  
- `DIFY_FORCE_ROTATE_KEY=0`：默认不轮转密钥，仅缺失时补齐。  
- 若 fallback 模型不稳定：先将 `DIFY_FALLBACK_MODEL` 设为与主模型一致。  

## 通过标准

`docs/ops/go_live_bundle_latest.json` 中：

- `overall = PASS`
- `steps.provider_recovery_and_smoke.ok = true`
- `steps.embedding_channel_ensure.ok = true`
- `steps.release_stability_check.overall = PASS`
- `steps.go_live_preflight.overall = PASS`

## 失败时优先排查

1. Provider：`artifacts/go_live_bundle/run_*/01_provider_recovery.log`
2. Embedding：`artifacts/go_live_bundle/run_*/02_embedding_channel.log`
3. 稳定性：`artifacts/go_live_bundle/run_*/03_release_stability.log`
4. Preflight：`artifacts/go_live_bundle/run_*/04_go_live_preflight.log`
5. 根因摘要：`docs/ops/go_live_failure_digest_latest.md`
6. 运行快照：`docs/ops/runtime_profile_snapshot.md`

## 每日自动运行（Cron）

详见：`docs/ops/go_live_bundle_cron_cn.md`
