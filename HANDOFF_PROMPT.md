# Lab Safety Assistant — 交接提示词

如果你（AI Agent）接手了本项目，请先阅读此文件以了解当前状态。

---

## 1. 项目基本信息

- **仓库**: `https://github.com/leilehuimieba/lab-safety-assistant`
- **本地路径**: `D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github`
- **分支**: `main`
- **技术栈**: Python 3.13, FastAPI, Vite, TypeScript, Tailwind CSS, pytest
- **当前产品名**: `实验安全前置哨（Lab Safety Copilot / 实验前安全检查助手）`
- **当前阶段**: `Phase 5 - no-Dify 需求重定位与轻量 MVP`
- **当前 active change**: `docs/changes/2026-04-28-demand-realignment-no-dify/`
- **pytest 交接口径**: `157 tests, 155 pass`（2 项 `test_eval_smoke.py` 失败待修复）

---

## 2. 当前主线口径

当前项目不再以 Dify/RAG 问答演示、申报书 `1000/3000` 知识库扩容或 v8.2 演示冻结作为第一目标。

当前主线是 no-Dify 自研轻量 MVP：

```text
学生实验前输入
  -> 风险识别
  -> 开工前检查清单
  -> 阻断 / 需老师确认 / 可开工
  -> 老师审核包
  -> 管理看板统计与低置信队列
```

当前核心判断：

> 本项目不是普通 AI 问答页，而是把实验前安全判断变成可操作、可阻断、可提交老师确认的轻量闭环。

Dify、v8.2 发布包和历史演示文档只保留为历史资产、可选兼容链路或回退参考，不作为当前 MVP Gate。

---

## 3. 最新文档入口

| 文档 | 路径 | 说明 |
|---|---|---|
| 执行入口 | `docs/README.md` | 当前主线、阶段、读取顺序和冲突优先级 |
| 文档索引 | `docs/INDEX.md` | 当前产品/验收/历史文档索引 |
| 路线图 | `docs/roadmap.md` | Phase 5 和阶段 Gate |
| 当前定位摘要 | `docs/product/current_positioning_20260501.md` | 最新定位和删旧文档后的统一口径 |
| no-Dify PRD | `docs/product/prd_lab_safety_copilot_no_dify_20260428.md` | 轻量 MVP 产品需求 |
| 需求规格说明书 | `docs/product/requirements_spec_20260429.md` | 完整功能、非功能、数据和验收要求 |
| 系统设计文档 | `docs/product/design_spec_20260429.md` | FastAPI、Vite SPA、规则、检索、Docker 设计 |
| MVP 验收清单 | `docs/ops/no_dify_mvp_acceptance_checklist.md` | no-Dify 主链路验收步骤 |
| active status | `docs/changes/2026-04-28-demand-realignment-no-dify/status.md` | 当前完成/未完成/下一步 |
| active tasks | `docs/changes/2026-04-28-demand-realignment-no-dify/tasks.md` | 当前任务清单 |

已删除/降级的旧口径文档包括申报书兑现版需求、差距矩阵、旧产品化草稿和旧命名需求/设计文件。若需恢复申报书或 Dify 主线，必须先切换或新建 change。

---

## 4. 已完成的核心工作

### 4.1 no-Dify 定位和文档清理

- 已确认当前产品方向：`实验安全前置哨 / Lab Safety Copilot / 实验前安全检查助手`
- 已确认 Dify 不再作为核心依赖，仅保留为历史 demo 或可选链路
- 已补充当前定位摘要：`docs/product/current_positioning_20260501.md`
- 已补充 no-Dify MVP 验收清单：`docs/ops/no_dify_mvp_acceptance_checklist.md`
- 已重写根 `README.md`，改为当前 no-Dify 主线入口
- 已更新 `docs/INDEX.md`、active change `status.md`、`tasks.md`
- 已将 `docs/guides/README_MVP_START.md` 和 `docs/guides/safety_rules_guide.md` 从 Dify starter 改为 no-Dify 本地规则口径

### 4.2 本地 bge-m3 语义检索集成

- 新增/维护 `libs/embedding_utils.py`
- 支持 `sentence-transformers` 和 `ollama` 双后端
- `ENABLE_EMBEDDING=0/1` 可动态关闭/启用语义检索
- `web_demo/services/kb_service.py` 支持文本 token + bge-m3 语义混合检索
- `scripts/eval_kb_retrieval.py` 可对比纯文本 vs 混合检索
- 知识库索引：`.cache/embedding/`（约 1,149 条向量条目）

### 4.3 应急卡片语义匹配

- `web_demo/services/emergency_service.py` 已支持应急卡片语义 + 文本混合匹配
- 应急卡片索引：`.cache/embedding_emergency/`（12 张卡片）
- 已验证示例：
  - `眼睛被酸溅到了` -> `chemical_splash`
  - `实验室着火了` -> `lab_fire`
  - `有人触电了` -> `electric_shock`
  - `化学品泄漏了` -> `chemical_leak`

### 4.4 前端与后端适配

- 已导入 Vite + TypeScript + Tailwind SPA 到 `web_demo/frontend/`
- 已完成 FastAPI 静态文件服务和 SPA fallback
- 已完成 API 兼容层、别名路由和数据模型适配
- 已修复若干后端导入缺失导致的 500 错误

### 4.5 Docker 封装

- `Dockerfile`: 多阶段构建
- `docker-compose.yml`: 一键启动，含健康检查和 volume 挂载
- `.dockerignore`: 排除开发/测试/日志文件
- `.github/workflows/build-and-push-image.yml`: CI/CD 多架构镜像构建
- `docs/ops/docker_deploy_guide.md`: Docker 部署文档

---

## 5. 关键配置速查

| 变量 | 默认值 | 说明 |
|---|---|---|
| `ENABLE_EMBEDDING` | `1` | `0` 关闭语义检索，便于本地快速验证 |
| `EMBEDDING_BACKEND` | `sentence-transformers` | `ollama` 或 `sentence-transformers` |
| `EMBEDDING_MODEL` | `BAAI/bge-m3` | HuggingFace 模型名 / Ollama 模型名 |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API 地址 |
| `SEMANTIC_WEIGHT` | `12.0` | 知识库语义权重 |
| `EMERGENCY_SEMANTIC_WEIGHT` | `6.0` | 应急卡片语义权重 |
| `DIFY_APP_API_KEY` | 空 | 可选历史链路；当前 no-Dify 主线不应依赖它 |

---

## 6. 启动和验证

### 6.1 本地启动

```powershell
cd D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github
powershell -ExecutionPolicy Bypass -File scripts\start_web_demo_local.ps1
```

默认地址：

```text
http://127.0.0.1:8088
```

手工调试：

```powershell
$env:ENABLE_EMBEDDING="0"
python -m uvicorn web_demo.app:app --host 127.0.0.1 --port 8088
```

### 6.2 测试

```powershell
python -m pytest -q
python scripts/quality_gate.py --repo-root . --skip-secret-scan
```

### 6.3 MVP 主链路验收

先看：

```text
docs/ops/no_dify_mvp_acceptance_checklist.md
```

推荐高风险测试场景：

```text
锂电池拆解，使用金属螺丝刀撬开外壳，未阅读 SOP，未穿绝缘手套，未获得老师批准。
```

期望：

1. 风险等级 High / Critical。
2. 检查清单包含 SOP、PPE、老师批准和电气/火灾专项项。
3. 缺关键项时 `allow_start=false`。
4. `blocking_reasons` 明确指出缺失项。
5. `review_status=pending`。
6. 老师可 approve/reject。
7. 管理看板可展示待审核、高风险或阻断原因。

---

## 7. 当前关键数据

| 指标 | 数值 |
|---|---|
| 知识库 CSV 条目 | 142 条（含 bge-m3 向量索引后约 1,149 条语义条目） |
| 安全规则 | 24 条（4 critical / 16 high / 3 medium / 1 low） |
| 应急卡片 | 12 张（覆盖 10 种事故类型） |
| 培训题库 | 50 题（10 类别，41 单选 + 9 多选） |
| pytest | 157 项（155 pass, 2 fail，按交接口径） |
| 前端页面 | 8 个 SPA 页面（Vite + TS + Tailwind） |
| 服务模块 | 10 个业务服务文件 |

---

## 8. 当前最小下一步

1. 按 `docs/ops/no_dify_mvp_acceptance_checklist.md` 跑一轮 API + 浏览器主链路验收。
2. 建立 FR-01 到 FR-09 的实现对齐表，标明对应 API、service、前端页面和测试文件。
3. 修复 `test_eval_smoke.py` 中剩余失败项，使 `python -m pytest -q` 全绿。
4. 提交当前文档清理结果，避免新旧需求口径混杂。
5. 如继续保留 v8.2 / Dify 文档，统一标注为“历史 / 可选链路”。
