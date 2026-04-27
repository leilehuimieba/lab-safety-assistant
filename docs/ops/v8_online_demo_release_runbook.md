# V8 在线演示链路执行手册

本手册对应三件事的一键落地：

1. 将 `release_exports/v7/knowledge_base_import_ready.csv` 导入当前 Dify 知识库  
2. 跑 20 题自动回归（Dify App API）  
3. 生成 V8 扩容批次并导出演示可用发布包  

## 1. 一键导入 + 20 题回归

在仓库根目录执行：

```powershell
powershell -File scripts/run_v7_dify_demo_chain.ps1
```

默认行为：

- 自动使用 `release_exports/v7/knowledge_base_import_ready.csv`
- 自动从本机 Dify 数据库识别数据集 `实验室安全知识库`
- 自动创建 dataset token（仅本机自部署 Dify 场景）
- 默认启用 `-WaitIndexing`（导入后等待索引完成再进入评测）
- 自动抓取最新 app token，并在评测前执行健康门禁（Dify 可达性）
- 评测默认启用 `--retry-on-timeout 1`，降低单题偶发超时对指标的影响

如需关闭等待索引（不推荐）：

```powershell
powershell -File scripts/run_v7_dify_demo_chain.ps1 -WaitIndexing:$false
```

如需临时关闭健康门禁（仅排障时）：

```powershell
powershell -File scripts/run_v7_dify_demo_chain.ps1 -SkipHealthGate
```

产物：

- `artifacts/dify_import_v7/import_report.json`
- `docs/eval/dify_import_v7_report.md`
- `artifacts/eval_smoke_v7_demo_chain/run_时间戳/summary.json`

## 2. 生成 V8 数据扩容发布包

```powershell
powershell -File scripts/run_v8_release.ps1
```

该流程会自动执行：

1. `web_seed_urls_v8_candidates.csv` 抓取
2. 预抓取状态生成（可抓取率/阻断率/低质率）
3. 低质量条目自动改写
4. 生成 `release_exports/v8/knowledge_base_import_ready.csv`

关键产物：

- `data_sources/web_seed_urls_v8_prefetch_status.csv`
- `docs/pipeline/web_seed_v8_prefetch_report.md`
- `release_exports/v8/knowledge_base_import_ready.csv`

## 3. 服务器一键启动 web_demo

Linux 服务器：

```bash
bash deploy/deploy_web_demo_server.sh
```

首次会自动生成 `.env.web_demo`，补好 `OPENAI_API_KEY` 后再运行一次即可。

常用命令：

```bash
bash deploy/start_web_demo.sh
bash deploy/status_web_demo.sh
bash deploy/stop_web_demo.sh
tail -f logs/web_demo.log
```

## 4. 失败排查

- Dify 导入 401：通常是 dataset token 缺失/失效，重新执行 `run_v7_dify_demo_chain.ps1`（保持 `-AutoProvisionDatasetToken` 开启）。
- Dify 回归失败：检查 `docker ps` 中 `docker-api-1/docker-nginx-1/docker-worker-1` 是否正常。
- web_demo 启动失败：优先检查 `.env.web_demo` 的 `OPENAI_API_KEY` 和 `logs/web_demo.log`。
