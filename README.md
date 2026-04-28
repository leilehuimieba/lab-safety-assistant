# 实验室安全小助手（Lab Safety Assistant）

面向高校实验室场景的实验室安全智能辅助系统。  
当前仓库以课程 / 大创展示为优先目标，已收敛到 `v8.2` 演示基线，并形成“问答 + 风险评估 + 开工前检查 + 培训考核 + 管理看板 + 事故复盘”的闭环演示版本。

## 1. 项目目标

1. 针对实验室安全问题给出可执行、可追溯的回答。
2. 所有知识条目可溯源（来源单位、来源链接、风险等级）。
3. 支持从公开资料自动抓取、清洗、重写、入库、发布的一键流程。
4. 先使用云端 API 快速验证，后续平滑切换本地模型。

## 2. 当前完成状态（可落地）

1. 已有主知识库：`knowledge_base_curated.csv`
2. 已有规则库：`safety_rules.yaml`
3. 已有评测集：`eval_set_v1.csv`
4. 已完成最新发布批次：`release_exports/v8.2/knowledge_base_import_ready.csv`
5. 已完成正式验收口径：知识库导入 `398` 条成功、20 题正式回归 `20/20`、连续 3 轮真实回归 `3/3 PASS`
6. 已提供发布/门禁脚本：`scripts/run_v8_2_release.ps1`、`scripts/run_eval_release_oneclick.ps1`
7. `web_demo` 已支持：
   - 实验室安全问答
   - 风险评估
   - 开工前检查清单与阻断
   - 培训考核与培训统计
   - 管理端看板
   - 事故复盘
8. 实验室安全问答唯一正式链路为 Dify 正式知识库工作流；结构化 fallback 仅用于链路异常兜底

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
│  ├─ changes/                   # 当前 change 工作区
│  ├─ templates/                 # change 模板
│  └─ word/                      # 可直接分发的 Word 执行手册
├─ release_exports/
│  ├─ v8/                        # 历史发布包
│  ├─ v8.1/                      # 历史发布包
│  └─ v8.2/                      # 当前演示基线发布包
├─ scripts/                      # 自动化脚本（抓取、清洗、评测、发布）
├─ skills/                       # 本地技能（含 web-content-fetcher）
├─ tests/                        # 回归测试
├─ web_demo/                     # 演示 API 与页面
│  ├─ routers/                   # FastAPI 路由（chat / risk / training / incident / admin / dify）
│  ├─ services/                  # 业务逻辑（kb / answer / llm_output / upstream / emergency / meta / risk / training / incident / dashboard）
│  ├─ models.py                  # Pydantic 模型
│  └─ repositories.py            # 数据访问与常量
├─ knowledge_base_curated.csv
├─ safety_rules.yaml
└─ eval_set_v1.csv
```

## 4. 关键入口

1. `release_exports/v8.2/knowledge_base_import_ready.csv`  
   直接可导入知识库的正式数据包。

2. `scripts/run_v8_2_release.ps1`  
   一键执行：抓取 -> 状态 -> 报告 -> 低质重写 -> 打包 -> 发布。

3. `web_demo/app.py`  
   演示 API（问答、风险评估、开工清单、培训、看板、事故复盘）。

4. `docs/ops/defense_alignment_cn.md`
   当前答辩材料统一口径入口。

## 5. 快速运行

### 5.0 当前默认项目根目录

```powershell
cd D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github
```

> 说明：旧 `D:\workspace` 仅保留为历史回退点，不再作为默认执行入口。

### 5.1 安装依赖

```powershell
pip install -r scripts/requirements-web-ingest.txt
pip install fastapi uvicorn pyyaml requests pydantic
```

### 5.2 运行 V8.2 一键发布

```powershell
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File scripts/run_v8_2_release.ps1
```

### 5.3 运行演示服务（当前推荐入口）

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_web_demo_local.ps1
```

成功后默认地址：

- `http://127.0.0.1:8088`

查看状态：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/status_web_demo_local.ps1
```

停止：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/stop_web_demo_local.ps1
```

如确需手工方式，再参考 `docs/ops/local_web_demo_windows_quickstart_cn.md` 与 `.env.web_demo`。

### 5.3A 本地接服务器 Dify（当前推荐的最短落地方案）

如果你本机还没有完整跑起 Dify，但服务器已经有可用的 Dify 环境，可以直接使用：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_local_demo_via_server_dify.ps1
```

默认会：

- 建立本地 SSH tunnel 到服务器 `175.178.90.193`
- 读取服务器 `.env.web_demo` 中的 `DIFY_APP_API_KEY`
- 在本地启动一个 bridge 版 `web_demo`
- 默认地址为 `http://127.0.0.1:8090`

停止命令：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/stop_local_demo_via_server_dify.ps1
```

详细说明见：

- `docs/ops/local_dify_bridge_quickstart_cn.md`

### 5.4 质量检查

```powershell
python -m pytest -q
python scripts/quality_gate.py --repo-root . --skip-secret-scan
```

## 6. 文档导航

1. [运行手册](docs/ops/runbook.md)
2. [答辩口径总表](docs/ops/defense_alignment_cn.md)
3. [提交版 / 展示版最小交付清单](docs/ops/submission_minimum_delivery_cn.md)
4. [高频追问快答版](docs/ops/defense_faq_quick_answers_cn.md)
5. [v8.2 演示主链路冻结文档](docs/ops/v8_2_demo_flow_freeze_cn.md)
6. [最终演示脚本冻结版](docs/ops/v8_2_demo_final_script_cn.md)
7. [现场执行卡](docs/ops/v8_2_demo_stage_card_cn.md)
8. [演示顺序冻结与备用方案](docs/ops/demo_freeze_runbook_cn.md)
9. [服务器部署说明](docs/ops/server_deploy_guide_cn.md)
10. [上线差距与推进计划](docs/ops/go_live_gap_and_next_actions_20260330.md)
11. [Systemd 常驻部署](docs/ops/systemd_web_demo_guide_cn.md)
12. [反向代理与 HTTPS](docs/ops/reverse_proxy_https_guide_cn.md)

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
  -DifyBaseUrl http://localhost:8081 `
  -DifyAppKey <app_key> `
  -SkipHealthCheck `
  -SkipCanary
```

10. [统一入库流程](docs/pipeline/unified_ingestion_pipeline.md)
11. [网页入库流程](docs/pipeline/web_ingestion_pipeline.md)
12. [评测看板](docs/eval/eval_dashboard.md)
13. [发布审核日志](docs/eval/release_review_log.md)

## 7. 当前答辩推荐口径

建议统一这样表述：

1. 项目当前定位是“实验室安全闭环演示系统”，不是泛化聊天工具。
2. 当前展示主线以 `v8.2` 为基线，答辩优先，不以 prod 正式上线为第一目标。
3. 当前可稳定讲的核心能力是：
   - 问答
   - 风险评估
   - 开工前检查与阻断
   - 培训考核与统计
   - 管理端看板
   - 事故复盘
4. 当前统一指标口径是：
   - 知识库导入 `398` 条成功
   - 20 题正式回归 `20/20`
   - 连续 3 轮真实回归 `3/3 PASS`
   - 当前剩余重点问题是延迟波动，不是正确率失稳
## 8. 说明

1. 本仓库不保存私有密钥和本地数据库文件。
2. 历史试验产物已清理；如需复现旧版本，请从 Git 历史提交恢复。

