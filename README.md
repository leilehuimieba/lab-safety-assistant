# 实验室安全助手平台（Lab Safety Assistant）

面向高校实验室场景的安全问答与风险辅助平台。  
当前仓库已完成一次框架收口：保留可运行主链路和 `v7` 发布数据，清理历史试验产物与无效版本文件。

## 1. 项目目标

1. 针对实验室安全问题给出可执行、可追溯的回答。
2. 所有知识条目可溯源（来源单位、来源链接、风险等级）。
3. 支持从公开资料自动抓取、清洗、重写、入库、发布的一键流程。
4. 先使用云端 API 快速验证，后续平滑切换本地模型。

## 2. 当前完成状态（可落地）

1. 已有主知识库：`knowledge_base_curated.csv`
2. 已有规则库：`safety_rules.yaml`
3. 已有评测集：`eval_set_v1.csv`
4. 已完成最新发布批次：`release_exports/v8.1/knowledge_base_import_ready.csv`
5. 已提供发布/门禁脚本：`scripts/run_v8_1_release.ps1`、`scripts/run_eval_release_oneclick.ps1`
6. `web_demo` 已支持：
   - 规则命中拦截
   - 低置信度入队
   - Dify 正式知识库工作流
   - Dify 异常时结构化 fallback 回答

## 3. 目录结构（清理后）

```text
lab-safe-assistant-github/
├─ data_sources/                 # 数据源清单与模板（当前保留 v7 + 模板）
├─ docs/
│  ├─ guides/                    # 快速入门与规则说明
│  ├─ ops/                       # 运行手册、SOP、部署说明
│  ├─ pipeline/                  # 数据入库/抓取/清洗流程文档
│  ├─ eval/                      # 评测、门禁、发布审核记录
│  ├─ proposal/                  # 立项书材料
│  ├─ reports/                   # 项目阶段报告
│  └─ word/                      # 可直接分发的 Word 执行手册
├─ release_exports/
│  ├─ v8/                        # 历史发布包
│  └─ v8.1/                      # 当前正式发布包
├─ scripts/                      # 自动化脚本（抓取、清洗、评测、发布）
├─ skills/                       # 本地技能（含 web-content-fetcher）
├─ tests/                        # 回归测试
├─ web_demo/                     # 演示 API 与页面
├─ knowledge_base_curated.csv
├─ safety_rules.yaml
└─ eval_set_v1.csv
```

## 4. 关键入口

1. `release_exports/v8.1/knowledge_base_import_ready.csv`  
   直接可导入知识库的正式数据包。

2. `scripts/run_v8_1_release.ps1`  
   一键执行：抓取 -> 状态 -> 报告 -> 低质重写 -> 打包 -> 发布。

3. `web_demo/app.py`  
   演示 API（问答、风险评估、检索）。

## 5. 快速运行

### 5.1 安装依赖

```powershell
pip install -r scripts/requirements-web-ingest.txt
pip install fastapi uvicorn pyyaml requests pydantic
```

### 5.2 运行 V8.1 一键发布

```powershell
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File scripts/run_v8_1_release.ps1
```

### 5.3 运行演示服务

```powershell
set DIFY_BASE_URL=http://127.0.0.1:8080
set DIFY_APP_API_KEY=你的_dify_app_key
set OPENAI_BASE_URL=https://api.tabcode.cc/openai
set OPENAI_API_KEY=你的密钥
set OPENAI_MODEL=gpt-5.2-codex
uvicorn web_demo.app:app --host 0.0.0.0 --port 8000 --reload
```

### 5.4 质量检查

```powershell
python -m pytest -q
python scripts/quality_gate.py --repo-root . --skip-secret-scan
```

## 6. 文档导航

1. [运行手册](docs/ops/runbook.md)
2. [演示脚本](docs/ops/demo_script.md)
3. [服务器部署说明](docs/ops/server_deploy_guide_cn.md)
4. [上线差距与推进计划](docs/ops/go_live_gap_and_next_actions_20260330.md)
5. [Systemd 常驻部署](docs/ops/systemd_web_demo_guide_cn.md)
6. [反向代理与 HTTPS](docs/ops/reverse_proxy_https_guide_cn.md)

发布前建议执行一键体检：

```bash
python scripts/release/go_live_preflight.py --repo-root .
```

发布前建议执行稳定性验收（3轮）：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_release_stability_check.ps1 `
  -RepoRoot . `
  -Rounds 3 `
  -IntervalSec 30 `
  -WorkflowId <workflow_id> `
  -DifyBaseUrl http://localhost:8080 `
  -DifyAppKey <app_key> `
  -SkipHealthCheck `
  -SkipCanary
```

7. [统一入库流程](docs/pipeline/unified_ingestion_pipeline.md)
8. [网页入库流程](docs/pipeline/web_ingestion_pipeline.md)
9. [评测看板](docs/eval/eval_dashboard.md)
10. [发布审核日志](docs/eval/release_review_log.md)

## 7. 说明

1. 本仓库不保存私有密钥和本地数据库文件。
2. 历史试验产物已清理；如需复现旧版本，请从 Git 历史提交恢复。
