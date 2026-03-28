# Live 回归阻塞记录（2026-03-28）

## 现象

- `run_eval_regression_pipeline.py` 可以通过 `/v1/parameters` 预检。
- 但在 `/v1/chat-messages` 预检阶段超时（默认 20s）。
- `quality_gate` 仍被 `route_success_rate` 连续两周不达标拦截。

## 已确认根因

从 `docker-worker-1` 日志可确认：

- embedding 通道指向 `host.docker.internal:11434`
- 当前该地址不可达（`Network is unreachable` / `Couldn't connect to server`）
- 触发 `InvokeServerUnavailableError` 与 `Request to Plugin Daemon Service failed-500`

结论：当前不是脚本逻辑问题，而是 Dify 检索链路依赖的 embedding 服务不可用。

## 修复方案（二选一）

### 方案 A（推荐）：修复现有 Ollama embedding 通道

1. 在宿主机启动可访问的 Ollama 服务（端口 `11434`）。
2. 确保 `docker-worker-1` 能访问该地址。
3. 在 Dify 的模型提供方中确认 embedding 模型配置（`bge-m3`）可用。

快速连通性检查：

```bash
docker exec docker-worker-1 sh -lc "curl -sS -m 3 http://host.docker.internal:11434/api/tags"
```

若返回模型列表则链路基本恢复。

### 方案 B：改用云端 embedding 模型

1. 在 Dify 中新增/切换一个可用的 embedding 提供方（OpenAI 兼容或官方 embedding）。
2. 把知识库检索节点关联到新的 embedding 模型。
3. 重新索引知识库（如有必要）。

## 修复后验证

```powershell
python scripts/run_eval_regression_pipeline.py `
  --repo-root . `
  --dify-base-url http://localhost:8080 `
  --dify-app-key <app-xxxx> `
  --limit 20 `
  --dify-timeout 30 `
  --eval-concurrency 4 `
  --update-dashboard
```

然后执行：

```powershell
python scripts/quality_gate.py --skip-secret-scan
```

通过标准：不再出现 `route_success_rate failed for 2 consecutive weeks`。
