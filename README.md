# 实验安全前置哨（Lab Safety Copilot）

面向高校实验教学和科研实验场景的轻量级实验前安全决策系统。

当前仓库的最新主线已经从“Dify/RAG 问答演示”切换为 **no-Dify 自研轻量版实验前安全检查助手**。项目现在优先解决的问题不是“AI 能不能回答一段安全知识”，而是：

> 学生准备开工前 1-2 分钟，系统能不能帮助判断“当前条件下到底能不能做”，并在高风险或缺关键条件时阻断、留痕、提交老师确认。

## 1. 当前定位

- 正式名称：`实验安全前置哨 —— 基于规则引擎与知识检索的实验前安全决策系统`
- 产品代号：`Lab Safety Copilot / 实验前安全检查助手`
- 当前阶段：`Phase 5 - no-Dify 需求重定位与轻量 MVP`
- 当前 active change：`docs/changes/2026-04-28-demand-realignment-no-dify/`
- 当前默认事实源：`D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github`

当前不再把 Dify 作为核心依赖。Dify、v8.2 发布包和历史演示材料只作为历史原型、可选兼容链路或证据参考，不作为当前 MVP Gate。

## 2. 当前目标

当前第一目标是打通并验证 no-Dify MVP 主闭环：

```text
学生实验前输入
  -> 风险识别
  -> 开工前检查清单
  -> 阻断 / 需老师确认 / 可开工
  -> 老师审核包
  -> 管理看板统计与低置信队列
```

核心交付不再是“一个问答机器人”，而是一个能输出结构化安全判断的实验前决策助手。

## 3. P0 功能范围

| 编号 | 功能 | 当前要求 |
|---|---|---|
| FR-01 | 实验前自查 / 安全问答 | 输入实验名称、试剂、设备、步骤、SOP/SDS/PPE 状态或自然语言安全问题 |
| FR-02 | 风险等级判断 | 识别 Low / Medium / High / Critical 等风险 |
| FR-03 | 阻断规则 | 高风险或缺关键项时输出 `暂不可开工` 或 `需老师确认` |
| FR-04 | 开工前检查清单 | 根据实验场景生成可勾选检查项 |
| FR-05 | 老师审核包 | 高风险/缺关键项提交给老师，展示风险、缺失项和建议动作 |
| FR-06 | 本地知识库问答 | 不依赖 Dify，从本地知识库返回带来源答案 |
| FR-07 | 来源引用 | 回答和建议要可追溯到来源标题、来源单位或链接 |
| FR-08 | 低置信问题队列 | 知识不足时不硬答，进入待补知识队列 |
| FR-09 | 管理看板 | 展示待审核、高风险场景、阻断原因、低置信问题等 |

P1/P2 能力包括应急卡片、培训考核、事故复盘、导出报告、登录权限、数据库迁移、真实试点反馈等；这些不应阻塞当前 MVP 主闭环。

## 4. 当前关键资产

| 类型 | 路径 | 说明 |
|---|---|---|
| 执行入口 | `docs/README.md` | 当前主线、阶段和文档优先级 |
| 路线图 | `docs/roadmap.md` | Phase 5 和阶段 Gate |
| active change | `docs/changes/2026-04-28-demand-realignment-no-dify/` | 当前推进状态、任务和验证口径 |
| 当前定位摘要 | `docs/product/current_positioning_20260501.md` | 最新产品定位和删旧文档后的统一口径 |
| PRD | `docs/product/prd_lab_safety_copilot_no_dify_20260428.md` | no-Dify 轻量 MVP 产品需求 |
| 正式需求规格 | `docs/product/requirements_spec_20260429.md` | 完整功能、非功能、数据和验收要求 |
| 系统设计 | `docs/product/design_spec_20260429.md` | FastAPI、Vite SPA、规则、检索、Docker 设计 |
| MVP 验收清单 | `docs/ops/no_dify_mvp_acceptance_checklist.md` | 当前主链路验证清单 |
| 知识库 | `knowledge_base_curated.csv` | 本地安全知识库 |
| 安全规则 | `safety_rules.yaml` | YAML 确定性规则引擎 |
| Web 应用 | `web_demo/app.py` | FastAPI 入口，服务 API 和 SPA 静态文件 |
| 前端源码 | `web_demo/frontend/` | Vite + TypeScript + Tailwind SPA |

## 5. 快速运行

```powershell
cd D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github
powershell -ExecutionPolicy Bypass -File scripts/start_web_demo_local.ps1
```

默认地址：

- `http://127.0.0.1:8088`

停止服务：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/stop_web_demo_local.ps1
```

状态检查：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/status_web_demo_local.ps1
```

手工调试方式：

```powershell
$env:ENABLE_EMBEDDING="0"
python -m uvicorn web_demo.app:app --host 127.0.0.1 --port 8088
```

> `ENABLE_EMBEDDING=0` 是本地快速验证默认建议。需要语义检索时再开启 Ollama / bge-m3。

## 6. 质量检查

```powershell
python -m pytest -q
python scripts/quality_gate.py --repo-root . --skip-secret-scan
```

当前交接口径中记录：pytest 共 157 项，155 pass，2 个 `test_eval_smoke.py` 相关失败待修复。后续应优先将其修到全绿，再作为“全部自动化测试通过”的交付口径。

## 7. 当前演示脚本

推荐只演示一条高风险主链路：

1. 学生输入高风险实验，例如“锂电池拆解，使用金属工具，未阅读 SOP，未穿绝缘手套”。
2. 系统输出 High / Critical 风险。
3. 系统生成开工前检查清单。
4. 学生故意不勾选 SOP、PPE、老师批准等关键项。
5. 系统返回 `allow_start=false`，展示明确 `blocking_reasons`。
6. 老师工作台出现待审核记录。
7. 老师查看风险、缺失项和建议动作，批准或驳回。
8. 管理看板显示待审核、高风险和阻断原因。

一句话收口：

> 我们不是做普通 AI 问答，而是把实验前安全判断变成可操作、可阻断、可提交老师确认的轻量闭环。

## 8. 历史材料说明

以下内容仍可作为历史证据或回退参考，但不作为当前主线 Gate：

- `release_exports/v8.2/`
- `docs/ops/v8_2_*`
- `docs/eval/dify_*`
- `docs/ops/local_dify_bridge_quickstart_cn.md`
- `scripts/run_local_demo_via_server_dify.ps1`

如果需要恢复申报书兑现或 Dify 平台主线，应先新建或切换 change，不要直接覆盖当前 no-Dify MVP 口径。
