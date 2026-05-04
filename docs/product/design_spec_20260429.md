# 实验安全前置哨 — 系统设计文档

> **项目正式名称**：实验安全前置哨 —— 基于规则引擎与知识检索的实验前安全决策系统
> **文档版本**：v2.0
> **日期**：2026-04-29
> **对应需求文档**：`docs/product/requirements_spec_20260429.md`
> **适用仓库**：`D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github`

---

## 1. 设计概述

### 1.1 设计目标

基于需求规格说明书，设计"实验安全前置哨"的完整技术架构，达成以下目标：

1. **本地可运行**：Docker 一键部署，单机即可运行全部功能，不依赖特定云平台
2. **安全确定性**：规则引擎在 LLM 调用前完成硬阻断，安全边界不受 prompt 不确定性影响
3. **轻量可测试**：pytest 157 项全覆盖，纯文本 fallback 确保无外部依赖时也可运行
4. **渐进可扩展**：模块化分层设计，CSV → SQLite → PostgreSQL 的平滑迁移路径
5. **快速迭代**：YAML 规则热生效、Vite SPA 热更新、JSON/CSV 数据可文本编辑

### 1.2 设计原则

| 原则 | 说明 |
|---|---|
| 安全兜底优先 | 任何环节失败时降级到安全结果（保守回答），不吐危险答案 |
| 规则优先于模型 | YAML 规则引擎在 LLM 之前执行，安全边界是确定性的 |
| Defensive Fallback | 语义检索失败 → 文本检索；LLM 失败 → 结构化答案；每个外部依赖都有降级路径 |
| 展示可复现优先 | 演示链路可稳定复现，非核心功能容忍降级 |
| 数据可迁移 | CSV/JSON 格式，非私有二进制，Excel 可直接打开 |
| 最小依赖 | MVP 阶段 CSV 文件存储，无需 MySQL/Redis/消息队列 |

### 1.3 技术选型总表

| 层面 | 选型 | 版本 | 选型理由 |
|---|---|---|---|
| Web 框架 | FastAPI | 0.115.6 | 异步支持、自动 OpenAPI 文档、Pydantic 深度集成 |
| ASGI 服务器 | uvicorn | 0.34.0 | 轻量、支持热重载、兼容 Windows/Linux |
| 数据校验 | Pydantic | 2.10.4 | 类型安全、自动序列化、IDE 友好 |
| 前端构建 | Vite | 5.2+ | 秒级 HMR、TypeScript 原生支持 |
| 前端语言 | TypeScript | 5.4+ | 类型安全、减少运行时错误 |
| 前端样式 | Tailwind CSS | 3.4+ | 原子化样式、JIT 编译、设计系统一致性 |
| 数据存储 | CSV + JSON 文件 | — | MVP 阶段零依赖持久化，Excel 可编辑 |
| 安全规则 | YAML | — (PyYAML 6.0.2) | 可读可编辑、非开发人员可维护、热生效 |
| 检索引擎 | 文本 Token + bge-m3 语义向量 | — | 双路混合召回，精确匹配+语义泛化互补 |
| Embedding 运行时 | Ollama | bge-m3 (1.2GB) | GPU 加速、API 调用、不占 Python 内存 |
| Embedding 备选 | sentence-transformers | 3.0+ | HuggingFace 直接加载、离线可用 |
| LLM 协议 | OpenAI-compatible API | — | 通用协议、可切任意兼容服务（本地/云端） |
| HTTP 客户端 | requests / httpx | 2.32.3 / 0.28 | 同步（FastAPI 路由内）+ 异步（SSE 流） |
| 容器化 | Docker + docker-compose | — | 一键部署、环境一致性 |
| CI/CD | GitHub Actions | — | 自动构建多架构镜像、推送 ghcr.io |
| 测试框架 | pytest | 8.0+ | 157 项测试、fixture 机制、参数化支持 |

---

## 2. 系统架构

### 2.1 四层架构

```
┌──────────────────────────────────────────────────────────────────┐
│                    前端层 (Presentation Layer)                     │
│                                                                   │
│  Vite 5 + TypeScript 5.4 + Tailwind CSS 3.4                      │
│  8 个 SPA 页面 (~30 个 .ts 文件)                                   │
│  CustomEvent 状态管理 + history.pushState 客户端路由               │
│  构建产物：纯静态文件 (dist/)，FastAPI 直接 serve                   │
└────────────────────────────┬─────────────────────────────────────┘
                             │ HTTP REST (JSON) + SSE (streaming)
┌────────────────────────────┴─────────────────────────────────────┐
│                    路由层 (Router Layer)                           │
│                                                                   │
│  web_demo/app.py         — FastAPI 入口 + 静态文件 + SPA fallback  │
│  web_demo/routers/       — 7 组 API 路由                          │
│                                                                   │
│  chat_routes.py     — /api/chat, /api/search, Dify 代理           │
│  risk_routes.py     — /api/risk/*, /api/checklist/*                │
│  emergency_routes.py — /api/emergency/*                            │
│  training_routes.py — /api/training/*                              │
│  incident_routes.py — /api/incidents/*                             │
│  admin_routes.py    — /api/admin/*, /api/workspace/*               │
│  meta_routes.py     — /, /health, /api/meta                        │
└────────────────────────────┬─────────────────────────────────────┘
                             │
┌────────────────────────────┴─────────────────────────────────────┐
│                    服务层 (Service Layer)                          │
│                                                                   │
│  web_demo/services/ — 10 个业务服务模块                            │
│                                                                   │
│  kb_service.py          — 知识库混合检索 + 规则引擎匹配            │
│  answer_service.py      — 答案构建 + 低置信判断 + 入队             │
│  risk_service.py        — 风险评估 + 检查清单生成 + 提交评估       │
│  emergency_service.py   — 应急卡片混合匹配                         │
│  training_service.py    — 题库管理 + 考核评分 + 统计               │
│  incident_service.py    — 事故 CRUD + 逾期/复发风险计算            │
│  dashboard_service.py   — 管理看板 + 周报 + CSV 导出               │
│  upstream_service.py    — LLM 调用封装 (Dify / OpenAI-compatible) │
│  llm_output_service.py  — LLM 输出清洗 + 乱码修复                  │
│  meta_service.py        — 应用元信息                               │
└────────────────────────────┬─────────────────────────────────────┘
                             │
┌────────────────────────────┴─────────────────────────────────────┐
│                    数据层 (Data Layer)                             │
│                                                                   │
│  web_demo/repositories.py  — 数据加载 + 全局缓存 + 路径常量        │
│                                                                   │
│  libs/common_io.py         — CSV/JSON 通用读写                     │
│  libs/text_utils.py        — 文本标准化 + 分词 + token 提取        │
│  libs/time_utils.py        — 时间解析 + 天数计算                   │
│  libs/embedding_utils.py   — bge-m3 语义向量（双后端）             │
│                                                                   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐ │
│  │ 本地文件系统       │  │ 向量缓存           │  │ 外部服务           │ │
│  │ CSV / JSON / YAML │  │ .cache/embedding/ │  │ Ollama / API      │ │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

### 2.2 核心数据链路（完整流程）

```text
                        POST /api/checklist/template
                                  │
                                  ▼
  ┌───────────────────────────────────────────────────────────────┐
  │  1. 文本预处理                                                  │
  │     normalize_search_text(scenario)                            │
  │     → 小写、去标点、中文分词混合、停用词过滤                       │
  └───────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
  ┌───────────────────────────────────────────────────────────────┐
  │  2. 规则引擎优先匹配 (在 LLM 调用前执行)                          │
  │     match_rule(scenario)                                       │
  │     → 遍历 24 条 YAML rules[*].patterns                         │
  │     → 匹配模式: keyword 子串匹配 + regex 正则匹配                 │
  │     → 返回: {id, severity, action, response, ...}              │
  │                                                                │
  │     如果 action == "refuse"                                     │
  │       → should_enforce_terminal_rule 返回 true                  │
  │       → 直接返回 build_rule_answer(rule, citations)              │
  │       → 不调用 LLM                                              │
  └───────────────────────────┬───────────────────────────────────┘
                              │ (未命中硬阻断)
                              ▼
  ┌───────────────────────────────────────────────────────────────┐
  │  3. 知识库混合检索                                              │
  │     retrieve_citations(question, top_k=5)                      │
  │                                                                │
  │     ┌─ 文本 Token 匹配 ─────────────────────────────┐          │
  │     │  extract_tokens(question)                      │          │
  │     │  → Jaccard similarity against kb[*].blob       │          │
  │     │  → text_score ∈ [0, 1]                         │          │
  │     └────────────────────────────────────────────────┘          │
  │                                                                │
  │     ┌─ bge-m3 语义检索 (ENABLE_EMBEDDING=1) ────────┐          │
  │     │  embed_query(question)                         │          │
  │     │  → cosine_similarity(query_vec, kb_index)      │          │
  │     │  → semantic_score ∈ [0, 1]                     │          │
  │     │  → fallback: 模型加载失败 → 自动跳过            │          │
  │     └────────────────────────────────────────────────┘          │
  │                                                                │
  │     最终得分 = text_score + 12.0 × semantic_score               │
  │     → 排序取 top_k → 构建 Citation 列表                         │
  └───────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
  ┌───────────────────────────────────────────────────────────────┐
  │  4. 风险评估                                                    │
  │     risk_score = max(rule_severity_score, max_citation_risk,    │
  │                      keyword_score)                             │
  │     clamp(risk_score, 1, 5)                                    │
  │                                                                │
  │     危险类型(HAZARD_HINTS): [Chemical, Electrical, Fire, ...]   │
  │     PPE推荐(PPE_HINTS): [Splash goggles, Lab coat, ...]        │
  └───────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
  ┌───────────────────────────────────────────────────────────────┐
  │  5. 检查清单生成                                                │
  │     items = BASE_CHECKLIST_ITEMS (6 项)                         │
  │     + HAZARD_CHECKLIST_ITEMS[each hazard] (每类 1 项)           │
  │     + HIGH_RISK_CHECKLIST_ITEMS (if risk_score ≥ 4, 2 项)       │
  │     → dedupe_checklist_items → ChecklistTemplateResponse        │
  └───────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
  ┌───────────────────────────────────────────────────────────────┐
  │  6. 学生提交检查清单                                            │
  │     比对 submitted_items vs template.checklist                  │
  │     critical 项未勾选 → blocking_reasons.append(item.label)     │
  │     allow_start = (len(blocking) == 0)                          │
  │     review_status = "pending" if blocking else "approved"       │
  │     → 写入 CHECKLIST_RUNS_FILE (CSV)                            │
  │     → 返回 ChecklistSubmitResponse (含三色决策卡数据)            │
  └───────────────────────────┬───────────────────────────────────┘
                              │ (review_status == "pending")
                              ▼
  ┌───────────────────────────────────────────────────────────────┐
  │  7. 老师审核                                                    │
  │     PATCH /api/checklist/{id}/review {action: approve|reject}   │
  │     → 更新 CSV 中 review_status/reviewed_by/reviewed_at/        │
  │       review_comment                                           │
  │     → 返回 ChecklistReviewResponse                             │
  └───────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
  ┌───────────────────────────────────────────────────────────────┐
  │  8. 管理看板聚合                                                │
  │     从各 CSV 文件聚合统计数据 → AdminDashboardResponse           │
  │     支持按天数/风险等级/事故状态筛选                               │
  └───────────────────────────────────────────────────────────────┘
```

---

## 3. 模块设计

### 3.1 路由层

#### 3.1.1 Chat Router (`routers/chat_routes.py`, 169 行)

**业务 API**：

| 端点 | 方法 | 功能 | 认证 |
|---|---|---|---|
| `/api/chat` | POST | 安全问答（主入口） | 无 |
| `/api/search` | GET | 知识库检索（仅返回 citations，不生成答案） | 无 |

**Dify 代理 API**（可选链路，保留向后兼容）：

| 端点 | 方法 | 功能 |
|---|---|---|
| `/v1/parameters` | GET | Dify 参数查询代理 |
| `/v1/chat-messages` | POST | Dify 对话消息代理（含 SSE 流式转发） |

**Chat 路由核心逻辑**：

```
chat(payload: ChatRequest) → ChatResponse:
  1. mode = "lab" | "agent"
  2. citations = retrieve_citations(question, 4) if lab else []
  3. rule = match_rule(question) if lab else None
  4. if rule and should_enforce_terminal_rule(question, rule):
        decision = "rule_blocked" | "emergency_redirect" | "need_more_info"
        return build_rule_answer(rule, citations)  # 不调用 LLM
  5. low_confidence, reason = assess_low_confidence(citations)
  6. try: answer, model = call_dify_lab(question) | call_upstream(...)
     except: answer = build_fallback_lab_answer(...)
  7. if low_confidence: append_low_confidence_followup(...) → CSV
  8. return ChatResponse(answer, citations, decision, ...)
```

#### 3.1.2 Risk Router (`routers/risk_routes.py`, 48 行)

| 端点 | 方法 | 功能 |
|---|---|---|
| `/api/risk/assess` | POST | 风险评估（主端点） |
| `/api/risk_assess` | POST | 风险评估（别名，向后兼容旧前端） |
| `/api/checklist/template` | POST | 生成检查清单模板 |
| `/api/checklist/submit` | POST | 提交检查清单结果 |
| `/api/checklist/{record_id}/review` | PATCH | 老师审核（approve/reject） |

**别名策略**：`/api/risk_assess` 是 `/api/risk/assess` 的别名，后端直接委托调用，无需前端修改。

#### 3.1.3 Emergency Router (`routers/emergency_routes.py`, 30 行)

| 端点 | 方法 | 功能 |
|---|---|---|
| `/api/emergency/cards` | GET | 返回全部 12 张应急卡片 |
| `/api/emergency/match` | GET | 应急场景匹配（query 参数） |
| `/api/emergency/match` | POST | 应急场景匹配（JSON body） |

**双方法支持**：GET 和 POST 均可用于应急匹配，兼容不同前端调用习惯。

#### 3.1.4 Training Router (`routers/training_routes.py`, 183 行)

| 端点 | 方法 | 功能 |
|---|---|---|
| `/api/training/questions` | GET | 获取随机题目（limit 参数控制数量） |
| `/api/training/submit` | POST | 提交答案并评分 |
| `/api/training/stats` | GET | 培训统计数据 |
| `/api/training/roster_status` | GET | 花名册完成状态 |
| `/api/training/roster` | GET | 花名册（别名） |
| `/api/training/roster_upload` | POST | 上传花名册 CSV（JSON body） |
| `/api/training/roster` | POST | 上传花名册 CSV（multipart form） |
| `/api/training/roster_template.csv` | GET | 下载花名册模板文件 |

**花名册匹配逻辑**：通过 student_id 或 name（大小写不敏感）匹配培训记录，取最新一次提交作为该学生的成绩状态。

#### 3.1.5 Incident Router (`routers/incident_routes.py`, 47 行)

| 端点 | 方法 | 功能 |
|---|---|---|
| `/api/incidents` | GET | 事故列表（支持 status 和 only_overdue 过滤） |
| `/api/incidents` | POST | 创建事故记录 |
| `/api/incidents/{incident_id}` | PATCH | 更新事故（状态流转 + 补充纠正措施） |
| `/api/incidents/{incident_id}` | DELETE | 删除事故记录 |

**状态筛选**：通过 query 参数 `?status=open&only_overdue=true` 组合筛选。

#### 3.1.6 Admin Router (`routers/admin_routes.py`, 113 行)

| 端点 | 方法 | 功能 |
|---|---|---|
| `/api/admin/dashboard` | GET | 管理看板数据 |
| `/api/admin/export.csv` | GET | 导出 CSV（4 种 scope） |
| `/api/admin/export` | GET | CSV 导出（别名） |
| `/api/admin/weekly_report.md` | GET | 导出 Markdown 周报 |
| `/api/admin/weekly-report` | GET | 周报导出（别名） |
| `/api/workspace/status` | GET | 工作区运行状态 |

**4 种导出 scope**：

| Scope | 数据源 | 返回字段 |
|---|---|---|
| checklists | CHECKLIST_RUNS_FILE | 16 字段（含 items_json） |
| training | TRAINING_ATTEMPTS_FILE | 9 字段 |
| low_confidence | LOW_CONFIDENCE_QUEUE_FILE | 17 字段 |
| incidents | INCIDENT_REVIEWS_FILE | 15+ 字段（含 recurrence_risk / overdue） |

#### 3.1.7 Meta Router (`routers/meta_routes.py`, 26 行)

| 端点 | 方法 | 功能 |
|---|---|---|
| `/` | GET | 返回前端 index.html（SPA 入口） |
| `/health` | GET | 健康检查 |
| `/api/meta` | GET | 应用元信息 |

#### 3.1.8 静态文件与 SPA 路由

**`/assets/{path:path}`**（app.py 中自定义）：
- 强制根据文件扩展名返回正确 MIME 类型
- 解决 Windows Python `mimetypes` 模块对 `.js`/`.mjs` 识别为 `text/plain` 的问题

**`/{path:path}`**（SPA fallback）：
- 非 `/api/`、非 `/assets/` 的路径全部返回 `index.html`
- 由前端 router 接管渲染 8 个客户端路由

---

### 3.2 服务层

#### 3.2.1 KB Service (`services/kb_service.py`)

**函数**：

```
retrieve_citations(query: str, top_k: int) → list[Citation]
```

**混合检索算法**：

```python
# Step 1: 文本 token 匹配
query_tokens = extract_tokens(normalize_search_text(query))
for entry in kb_entries:
    entry_tokens = extract_tokens(entry["blob"])
    text_score = jaccard_similarity(query_tokens, entry_tokens)
    scores.append({"entry": entry, "text_score": text_score})

# Step 2: bge-m3 语义检索（可选）
if ENABLE_EMBEDDING:
    query_vec = embed_query(query)  # Ollama / sentence-transformers
    semantic_scores = cosine_similarity(query_vec, kb_index)
    for i, score in enumerate(semantic_scores):
        scores[i]["semantic_score"] = score

# Step 3: 混合排序
for s in scores:
    s["final_score"] = s["text_score"] + SEMANTIC_WEIGHT * s.get("semantic_score", 0)

# Step 4: Top-K
scores.sort(key="final_score", reverse=True)
return top_k as list[Citation]
```

**语义检索降级**：当 `ENABLE_EMBEDDING=0`、模型加载失败、Ollama 不可用时，语义部分自动跳过，仅用文本分数排序。

```
match_rule(question: str) → dict | None
```

**匹配策略**：
1. 遍历 `safety_rules.yaml` 中 `rules[*].patterns`
2. 每个 pattern 支持两种匹配：`keyword`（子串包含）和 `regex`（正则）
3. 按规则文件中定义的优先级返回第一个匹配（severity 高的规则排在前面）
4. 无匹配返回 None

```
should_enforce_terminal_rule(question: str, rule: dict) → bool
```

**终端规则判断**：
1. 检查 `REFUSE_INTENT_MARKERS`（18 个高危意图模式）：如"能不能绕过""不戴手套""直接倒""下水道"等
2. 检查 `EMERGENCY_INTENT_MARKERS`（13 个应急意图模式）：如"怎么办""着火""泄漏""受伤"等
3. 匹配即返回 true，触发终端动作（拒绝/重定向/追问）

#### 3.2.2 Risk Service (`services/risk_service.py`, 238 行)

**函数**：

```
build_risk_assessment(scenario, citations, rule) → RiskAssessResponse
  ├── severity_score: SEVERITY_SCORE[rule.severity]  (critical=5, high=4, medium=3, low=2)
  ├── citation_score: max(citations[*].risk_level) or 1
  ├── keyword_score: 5 if high_risk_keywords present else 3
  ├── risk_score: clamp(max(severity, citation, keyword), 1, 5)
  ├── hazards: HAZARD_HINTS dictionary match against normalized text
  ├── ppe: PPE_HINTS dictionary match against text + citation snippets
  └── return RiskAssessResponse

build_checklist_template(scenario) → ChecklistTemplateResponse
  ├── citations = retrieve_citations(scenario, 5)
  ├── assessment = build_risk_assessment(scenario, citations, rule)
  ├── items = BASE_CHECKLIST_ITEMS (6)
  ├── + HAZARD_CHECKLIST_ITEMS[each_hazard] (1 per type)
  ├── + HIGH_RISK_CHECKLIST_ITEMS (2) if risk_score >= 4
  ├── + scope_defined item if no hazards identified
  └── → dedupe(items) → ChecklistTemplateResponse

evaluate_checklist_submission(payload) → ChecklistSubmitResponse
  ├── template = build_checklist_template(payload.scenario)  # 重新生成
  ├── for each critical item in template:
  │     if not submitted.checked → blocking.append(item.label)
  ├── allow_start = not blocking
  ├── review_status = "pending" if blocking else "approved"
  └── → write CSV row → ChecklistSubmitResponse

review_checklist_submission(record_id, payload) → ChecklistReviewResponse
  ├── read CSV → find record by record_id
  ├── update review_status/reviewed_by/reviewed_at/review_comment
  └── → rewrite CSV → return response
```

**风险评分矩阵**：

| 条件组合 | 分值 | 示例场景 |
|---|---|---|
| 规则 severity=critical + 高危关键词 | 5 | 金属钠遇水、易燃溶剂明火加热 |
| 规则 severity=high + 高危关键词 | 5 | 浓硫酸稀释、锂电池拆解 |
| 知识库最高风险=4 + 无规则命中 | 4 | SDS 标注为高风险的物质 |
| 知识库最高风险=3 + 无高危关键词 | 3 | 常规有机合成 |
| 知识库最高风险=1~2 | 1~2 | 物理测量、水溶液配制 |

#### 3.2.3 Answer Service (`services/answer_service.py`)

**函数**：

```
assess_low_confidence(citations) → (bool, str)
  └── top citation score < LOW_CONFIDENCE_TOP_SCORE (3.5) → True

build_rule_answer(rule, citations) → str
  └── 从 YAML 规则的 response 字段生成格式化回答
      含：结论 → 禁止事项 → 建议动作 → 引用来源

build_fallback_lab_answer(question, citations, rule, low_confidence_reason) → str
  └── 结构化 fallback 模板:
      ## 结论
      ## 处置步骤
      ## 禁止事项
      ## 升级建议
      ## 引用来源

append_low_confidence_followup(question, mode, decision, ...) → bool
  └── 写入 LOW_CONFIDENCE_QUEUE_FILE (17 字段, CSV 追加)

append_low_confidence_followup_notice(answer) → str
  └── 在回答末尾追加 "该回答置信度较低，建议联系实验室老师确认"
```

#### 3.2.4 Emergency Service (`services/emergency_service.py`)

**函数**：

```
to_emergency_card(item) → EmergencyCard
  └── JSON dict → Pydantic EmergencyCard 模型

match_emergency_card(query) → EmergencyMatchResponse
  ├── bge-m3 语义检索：cosine_similarity(query_vec, emergency_index)
  ├── 文本 token 匹配：Jaccard(tokenize(query), tokenize(card.blob))
  ├── 混合排序（EMERGENCY_SEMANTIC_WEIGHT=6.0）
  └── 返回 top-1 匹配卡片 + confidence 分数
```

#### 3.2.5 Training Service (`services/training_service.py`)

**函数**：

```
get_training_questions(limit=5) → list[dict]
  └── random.sample(training_bank, limit) 不重复抽取

to_public_question(item) → TrainingQuestionPublic
  └── dict → Pydantic, 去除答案字段

grade_training_submit(payload) → TrainingSubmitResponse
  ├── 逐题比对 selected_indices == correct_indices
  ├── score = 正确题数 / 总题数 * 100
  ├── passed = score >= pass_threshold (默认 80)
  ├── weak_categories: 错题所属类别去重
  ├── review: 每题的正确答案 + 解释 + 参考资料
  ├── → 写入 attempts CSV + mistakes CSV
  └── → TrainingSubmitResponse

load_training_stats() → TrainingStatsResponse
  └── 从 CSV 聚合：attempt_count / pass_rate / avg_score / category_mistakes / recent_scores
```

#### 3.2.6 Incident Service (`services/incident_service.py`)

**函数**：

```
load_incident_records() → list[IncidentRecord]
  └── 读 CSV → 解析 JSON 列表字段 → 计算 overdue/recurrence_risk

create_incident_record(payload) → IncidentRecord
  └── 生成 ID → 当前时间戳 → 写入 CSV

update_incident_record(id, payload) → IncidentRecord
  └── 按 id 定位 → 更新字段 → 重写 CSV

compute_incident_due_state(due_date, status) → (bool, int)
  └── due_date < today and status != "closed" → overdue=true, days=差值

compute_incident_recurrence_risk(severity, history) → str
  └── severity=critical 或同类事故 > 2 次 → "high"
```

#### 3.2.7 Dashboard Service (`services/dashboard_service.py`)

**函数**：

```
load_admin_dashboard(days, risk_level, incident_status) → AdminDashboardResponse
  ├── metrics: 检查单数、待审核数、培训通过率等
  ├── low_confidence_top: 按类别聚合低置信队列
  ├── recent_high_risk_scenarios: 高风险检查清单记录 (top 10)
  ├── incident_summary: 按状态统计 {open:3, in_review:1, ...}
  └── overdue_incidents: 逾期未处理事故列表

build_workspace_status() → WorkspaceStatusResponse
  ├── Dify 连接状态检测
  ├── 知识库条数 + 导入数
  ├── 低置信队列条目数
  └── top_categories / top_hazards 分布

build_weekly_report_markdown(days, ...) → str
  └── 生成 Markdown 格式周报，含核心指标、高风险列表、待处理事项

export_rows_to_csv(headers, rows) → str
  └── CSV 序列化，返回 text/csv 响应
```

#### 3.2.8 Upstream Service (`services/upstream_service.py`)

**LLM 调用封装**：

```
call_dify_lab(question) → (answer: str, model: str)
  ├── 构造 Dify API 请求 (chat-messages endpoint)
  ├── 解析 SSE 流式响应 (iter_sse_payloads + parse_sse_answer)
  ├── 超时: DIFY_TIMEOUT (默认 120s)
  └── 失败: 抛 HTTPException → 上层 fallback

call_upstream(mode, question, citations, guardrail) → (answer: str, model: str)
  ├── 构造 OpenAI-compatible 请求
  ├── build_system_prompt(mode) + build_user_message(question, citations, guardrail)
  ├── 模型: OPENAI_MODEL (默认 gpt-5.2-codex)
  ├── fallback 模型链: FALLBACK_MODELS (逗号分隔)
  └── 解析 SSE 流式响应
```

#### 3.2.9 LLM Output Service (`services/llm_output_service.py`)

```
sanitize_llm_output(text) → str
  └── 移除不安全输出模式

fix_mojibake_text(text) → str
  └── 修复 LLM 输出的乱码（如 Latin-1 被误判为 UTF-8 导致的乱码）
```

---

### 3.3 数据层

#### 3.3.1 Repositories (`repositories.py`, 436 行)

**路径常量**：

| 常量 | 值 | 存储内容 |
|---|---|---|
| `BASE_DIR` | `web_demo/` 父目录 | web_demo 自身目录 |
| `REPO_ROOT` | 项目根目录 | — |
| `KB_FILE` | `REPO_ROOT / knowledge_base_curated.csv` | 知识库主文件 |
| `RULES_FILE` | `REPO_ROOT / safety_rules.yaml` | 安全规则配置 |
| `EMERGENCY_CARDS_FILE` | `BASE_DIR / data / emergency_cards.json` | 应急卡片 |
| `TRAINING_BANK_FILE` | `BASE_DIR / data / training_question_bank.json` | 培训题库 |
| `LOW_CONFIDENCE_QUEUE_FILE` | `REPO_ROOT / artifacts/.../data_gap_queue.csv` | 低置信队列 |
| `CHECKLIST_RUNS_FILE` | `REPO_ROOT / artifacts/.../checklist_runs.csv` | 检查清单记录 |
| `TRAINING_ATTEMPTS_FILE` | `REPO_ROOT / artifacts/.../training_attempts.csv` | 培训记录 |
| `TRAINING_MISTAKES_FILE` | `REPO_ROOT / artifacts/.../training_mistakes.csv` | 错题记录 |
| `INCIDENT_REVIEWS_FILE` | `REPO_ROOT / artifacts/.../incident_reviews.csv` | 事故记录 |

**核心默认值**：

| 常量 | 默认值 | 说明 |
|---|---|---|
| `DEFAULT_TOP_K` | 4 | 知识库检索返回条数 |
| `DEFAULT_LOW_CONFIDENCE_TOP_SCORE` | 3.5 | 低置信判断阈值 |
| `DEFAULT_TRAINING_PASS_THRESHOLD` | 80 | 培训通过分数线 |
| `DIFY_DEFAULT_TIMEOUT` | 120.0 | Dify 请求超时（秒） |
| `SEVERITY_SCORE` | {critical:5, high:4, medium:3, low:2} | 严重性到数值映射 |
| `RISK_LABEL` | {1:Low, 2:Medium-Low, 3:Medium, 4:High, 5:Critical} | 评分到标签映射 |

**词典数据**：

| 词典 | 条目数 | 用途 |
|---|---|---|
| `PPE_HINTS` | 7 类 | PPE 关键词匹配推荐 |
| `HAZARD_HINTS` | 6 类 | 危险类型关键词匹配 |
| `BASE_CHECKLIST_ITEMS` | 6 项 | 所有实验通用的检查项 |
| `HAZARD_CHECKLIST_ITEMS` | 6 类 × 1 项 | 危险类型专项检查项 |
| `HIGH_RISK_CHECKLIST_ITEMS` | 2 项 | 高风险追加检查项 |
| `REFUSE_INTENT_MARKERS` | 18 个 | 硬阻断意图识别模式 |
| `EMERGENCY_INTENT_MARKERS` | 13 个 | 应急意图识别模式 |
| `TERMINAL_ACTIONS` | {refuse, redirect_emergency, ask_for_more_info} | 终端动作集合 |

**全局缓存机制**：
- 知识库、规则、应急卡片、题库均为懒加载 + 全局内存缓存
- `threading.Lock()` 线程安全
- Embedding 索引单独管理（`libs/embedding_utils.py`）

#### 3.3.2 Common IO (`libs/common_io.py`)

```
read_csv(path) → list[dict[str, str]]
write_csv(path, rows, fieldnames) → None
write_csv_row(path, headers, row_dict) → None  (追加模式)
load_json_list(path) → list[dict]
safe_read_csv_rows(path) → list[dict]  (文件不存在返回空列表)
```

#### 3.3.3 Text Utils (`libs/text_utils.py`)

```
normalize_search_text(text) → str
  └── 小写化、去标点、保留中英文字符和数字

extract_tokens(text) → list[str]
  └── 英文按空格分词，中文按字符 2-gram 组合

jaccard_similarity(tokens_a, tokens_b) → float
  └── |A ∩ B| / |A ∪ B|
```

#### 3.3.4 Time Utils (`libs/time_utils.py`)

```
parse_datetime(s) → datetime | None
within_days(date_str, days) → bool
```

#### 3.3.5 Embedding Utils (`libs/embedding_utils.py`, ~300 行)

**双后端架构**：

```
Embedding Backend Selection:
  EMBEDDING_BACKEND = "ollama" | "sentence-transformers"

  ┌─ ollama ───────────────────────────────────────┐
  │  Ollama API: POST /api/embed                    │
  │  Model: bge-m3 (1.2GB, GPU accelerated)         │
  │  Base URL: OLLAMA_BASE_URL                      │
  │  Default: http://localhost:11434                 │
  │  Docker: http://host.docker.internal:11434       │
  └─────────────────────────────────────────────────┘

  ┌─ sentence-transformers ────────────────────────┐
  │  HuggingFace: SentenceTransformer("BAAI/bge-m3")│
  │  Device: CPU (EMBEDDING_DEVICE)                 │
  │  First download: ~1.2GB                          │
  │  Auto-download from HuggingFace hub              │
  └─────────────────────────────────────────────────┘
```

**索引管理**：

```python
_index_states: dict[str, dict] = {}
# Keys:
#   "knowledge_base" → {"texts": [...], "embeddings": np.array, "path": Path}
#   "emergency_cards" → {"texts": [...], "embeddings": np.array, "path": Path}
```

**索引持久化**：
- 首次计算后 pickle 序列化到 `.cache/embedding/` 和 `.cache/embedding_emergency/`
- 每次启动检测文件是否存在，存在则直接加载（秒级），不存在则重新计算（10~30s）
- 文件包含 texts 和 embeddings numpy array

**核心函数**：

```python
embed_query(text: str) → np.ndarray
  └── 调用当前 backend 对单条文本编码

build_index(texts: list[str], dataset_name: str) → None
  └── 批量编码 + 持久化

load_index(dataset_name: str) → dict | None
  └── 从 .cache 加载已有索引

search_similar(texts: list[str], query_vec, top_k) → list[(idx, score)]
  └── cosine_similarity 矩阵运算 → 返回 top_k 索引和分数

ensure_index(dataset_name, texts) → None
  └── 索引不存在则自动构建
```

**环境变量控制**：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `EMBEDDING_BACKEND` | `sentence-transformers` | 后端选择 |
| `EMBEDDING_MODEL` | `BAAI/bge-m3` | 模型名 |
| `EMBEDDING_DEVICE` | `cpu` | sentence-transformers 推理设备 |
| `ENABLE_EMBEDDING` | `0`（web_demo app.py 默认） | 全局开关 |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API 地址 |
| `SEMANTIC_WEIGHT` | `12.0` | 知识库语义检索权重 |
| `EMERGENCY_SEMANTIC_WEIGHT` | `6.0` | 应急卡片语义检索权重 |

---

## 4. 数据模型

### 4.1 核心请求/响应模型（Pydantic, `models.py` 324 行）

#### 安全问答

```python
class ChatRequest(BaseModel):
    mode: str = "lab"              # "lab" | "agent"
    question: str                  # 1-4000 chars

class ChatResponse(BaseModel):
    answer: str
    mode: str
    model: str
    decision: str                  # llm_answer | rule_blocked | ...
    risk_level: str
    matched_rule_id: str
    matched_rule_action: str       # refuse | redirect_emergency | ...
    low_confidence: bool
    low_confidence_reason: str
    followup_logged: bool
    citations: list[Citation]
```

#### 引用

```python
class Citation(BaseModel):
    kb_id: str
    title: str
    source_title: str = ""
    source_org: str = ""
    source_url: str = ""
    risk_level: str = ""
    snippet: str = ""
    score: float = 0.0
```

#### 风险评估

```python
class RiskAssessRequest(BaseModel):
    scenario: str                  # 1-6000 chars

class RiskAssessResponse(BaseModel):
    scenario: str
    risk_score: int                # 1-5
    risk_level: str                # Low | Medium-Low | Medium | High | Critical
    key_hazards: list[str]         # [Chemical, Electrical, Fire, ...]
    ppe: list[str]                 # [Splash goggles, Lab coat, ...]
    forbidden: list[str]
    emergency_actions: list[str]
    recommended_steps: list[str]
    low_confidence: bool
    low_confidence_reason: str
    citations: list[Citation]
```

#### 检查清单

```python
class ChecklistItem(BaseModel):
    id: str                        # sop_reviewed | ppe_ready | ...
    label: str                     # 检查项原文
    critical: bool                 # 是否为关键项（阻断条件）
    checked: bool = False          # 学生提交的勾选状态
    note: str = ""                 # 学生备注

class ChecklistTemplateResponse(BaseModel):
    scenario: str
    risk_score: int
    risk_level: str
    key_hazards: list[str]
    checklist: list[ChecklistItem]
    recommended_actions: list[str]
    citations: list[Citation]

class ChecklistSubmitResponse(BaseModel):
    record_id: str                 # CHK-YYYYMMDD-XXXXXXXX
    submitted_at: str              # ISO timestamp
    scenario: str
    operator: str
    risk_score: int
    risk_level: str
    key_hazards: list[str]
    allow_start: bool              # ★ 核心决策字段
    blocking_reasons: list[str]    # ★ 阻断原因
    next_actions: list[str]
    review_status: str             # pending | approved | rejected
    reviewed_by: str
    reviewed_at: str
    review_comment: str
```

#### 应急卡片

```python
class EmergencyCard(BaseModel):
    id: str                        # chemical_splash | lab_fire | ...
    title: str
    category: str
    summary: str
    trigger_signs: list[str]
    immediate_actions: list[str]
    forbidden: list[str]
    ppe: list[str]
    escalation: list[str]

class EmergencyMatchResponse(BaseModel):
    query: str
    matched_card_id: str
    confidence: float
    card: EmergencyCard | None
```

#### 培训

```python
class TrainingSessionResponse(BaseModel):
    session_id: str                # SESSION-YYYYMMDDHHMMSS-XXXXXX
    total_questions: int
    pass_threshold: int            # 默认 80
    questions: list[TrainingQuestionPublic]

class TrainingSubmitResponse(BaseModel):
    attempt_id: str
    session_id: str
    participant: str
    submitted_at: str
    score: int
    total_questions: int
    pass_threshold: int
    passed: bool
    weak_categories: list[str]
    recommended_actions: list[str]
    review: list[TrainingReviewItem]  # 逐题回顾
```

#### 管理看板

```python
class AdminDashboardResponse(BaseModel):
    metrics: list[DashboardMetric]
    low_confidence_top: list[DashboardLowConfidenceItem]
    recent_high_risk_scenarios: list[DashboardHighRiskScenario]
    incident_summary: dict[str, int]  # {open:3, in_review:1, ...}
    overdue_incidents: list[str]
```

### 4.2 前后端数据类型同步

前端 TypeScript 类型定义应与后端 Pydantic 模型字段一一对应，在 `web_demo/frontend/src/types/` 中定义，通过 `api/client.ts` 的泛型函数保证类型安全：

```typescript
// types/models.ts (约 30 个 interface)
interface ChatRequest { mode: string; question: string; }
interface ChatResponse { answer: string; mode: string; /* ... */ citations: Citation[]; }
interface RiskAssessResponse { scenario: string; risk_score: number; /* ... */ }
// ...

// api/client.ts
async function post<TReq, TRes>(url: string, body: TReq): Promise<TRes> { /* ... */ }
```

---

## 5. 前端架构

### 5.1 技术栈

| 技术 | 版本 | 用途 |
|---|---|---|
| Vite | 5.2+ | 开发服务器 + 生产构建 |
| TypeScript | 5.4+ | 类型安全 |
| Tailwind CSS | 3.4+ | 原子化 CSS，JIT 编译 |
| PostCSS | 8.4+ | CSS 后处理（Autoprefixer） |
| 包管理 | pnpm 9.0 | 快速、磁盘节省 |

### 5.2 目录结构

```
web_demo/frontend/
├── index.html                  # SPA 入口
├── package.json                # pnpm 依赖配置
├── tsconfig.json               # TypeScript 配置
├── vite.config.ts              # Vite 配置（base: './'）
├── tailwind.config.js          # Tailwind 主题配置
├── postcss.config.js           # PostCSS 插件
├── src/
│   ├── main.ts                 # 应用入口，注册 CustomEvent 监听
│   ├── router.ts               # 客户端 Hash/History Router
│   ├── types/                  # TypeScript 类型定义（~20+ 文件）
│   ├── api/                    # API 请求封装层（~8 文件）
│   │   └── client.ts           # 通用 fetch 封装 + 错误处理
│   ├── store/                  # 轻量状态管理（CustomEvent pub/sub）
│   ├── components/             # 可复用 UI 组件（~15+ 文件）
│   │   ├── DecisionCard.ts     # 三色决策卡片（红/黄/绿）
│   │   ├── AppShell.ts         # 应用外壳布局
│   │   ├── NavBar.ts           # 导航栏
│   │   ├── ChecklistForm.ts    # 检查清单表单
│   │   ├── CitationPanel.ts    # 引用来源面板
│   │   ├── EmergencyCard.ts    # 应急卡片组件
│   │   └── ...
│   ├── pages/                  # 8 个页面组件
│   │   ├── HomePage.ts         # 首页 / 安全问答
│   │   ├── ChecklistPage.ts    # 开工前检查
│   │   ├── EmergencyPage.ts    # 应急卡片
│   │   ├── TrainingPage.ts     # 培训考核
│   │   ├── TeacherPage.ts      # 老师审核工作台
│   │   ├── AdminPage.ts        # 管理看板
│   │   ├── IncidentsPage.ts    # 事故管理
│   │   └── StatusPage.ts       # 系统状态
│   └── styles/                 # 全局样式
│       └── index.css           # Tailwind 指令 + 自定义主题变量
└── dist/                       # 构建产物（FastAPI 直接 serve）
    ├── index.html
    └── assets/
        ├── main-XXXXXXXX.js    # ~30KB gzipped
        └── main-XXXXXXXX.css   # ~10KB gzipped
```

### 5.3 客户端路由（SPA）

| 路径 | 页面 | 对应功能需求 |
|---|---|---|
| `/` | 安全问答首页 | FR-01 |
| `/checklist` | 开工前检查 | FR-02, FR-03 |
| `/emergency` | 应急卡片 | FR-06 |
| `/training` | 培训考核 | FR-07 |
| `/teacher` | 老师审核工作台 | FR-04 |
| `/admin` | 管理看板 | FR-05 |
| `/incidents` | 事故管理 | FR-08 |
| `/status` | 系统状态 | — |

路由方案：`history.pushState` + `popstate` 事件监听，无需引入 vue-router 或 react-router。

### 5.4 核心交互设计

**三色决策卡片（系统视觉中心）**：

```
allow_start=true, review_status=approved
  → 绿色卡片：✅ 检查通过，可以开工
     "请严格遵守 SOP，持续关注异常情况"

allow_start=false
  → 红色卡片：⛔ 暂不可开工
     逐条列出阻断原因（每条可操作）

risk_score ≥ 4, allow_start=true
  → 黄色卡片：⚠️ 需老师确认
     "你的实验风险较高，开工前必须经老师审核"
```

**Critical 项视觉标识**：红色左边框 + 红色星号标记，帮助用户快速聚焦关键检查项。

### 5.5 字体策略

使用系统字体栈，不依赖 Google Fonts（解决中国大陆网络环境下字体加载阻塞问题）：

```css
font-family: system-ui, -apple-system, "Segoe UI", "PingFang SC",
             "Microsoft YaHei", "Helvetica Neue", Arial, sans-serif;
```

---

## 6. 安全设计

### 6.1 安全问答防护链（四层防护）

```
Layer 1: 规则引擎硬阻断 (YAML)
  ├── 24 条确定性规则
  ├── refuse (8 条): "绕过""不戴手套""直接倒""明火加热"等 → 直接拒绝
  ├── redirect_emergency (13 条): "着火""泄漏""触电"等 → 引导应急卡片
  └── ask_for_more_info (1 条): 信息不足 → 追问
  ↓
Layer 2: 低置信度兜底
  ├── top_score < 3.5 → low_confidence=true
  ├── 不硬答，明确提示"建议联系老师"
  └── 自动入队
  ↓
Layer 3: LLM 输出安全清洗
  └── sanitize_llm_output + fix_mojibake_text
  ↓
Layer 4: 结构化 Fallback
  └── LLM 调用失败 → build_fallback_lab_answer
```

### 6.2 风险阻断链

```
场景输入 → 规则匹配 → 风险评估
  ↓
risk_score ≥ 4 → 追加高风险检查项（导师批准 + 单人操作管控）
  ↓
学生提交 → 逐项比对 critical 项
  ├── 全部通过 → allow_start=true, auto_approved
  └── 缺失 → allow_start=false, review_status=pending
      ↓
      老师审核 → approved/rejected
      所有决策写入 CSV，完整证据链可追溯
```

### 6.3 系统安全

| 层面 | 措施 |
|---|---|
| 密钥管理 | `.env.web_demo` 在 `.gitignore` 中，通过 docker-compose `env_file` 注入 |
| 输入校验 | Pydantic `min_length` / `max_length` / `pattern` 约束 |
| 文件路径 | 数据目录固定在项目内，无路径遍历风险 |
| CORS | 默认无跨域限制（MVP 阶段，后续可加白名单） |
| Docker | 非 root 用户运行（`python:3.13-slim` 基础镜像） |

---

## 7. 部署架构

### 7.1 Docker 部署拓扑

```
┌──────────────────────────────────────────────────────────────┐
│                     Docker Host                               │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  lab-safe-assistant (:8088)                               │ │
│  │  Image: python:3.13-slim, multi-stage build               │ │
│  │  CMD: uvicorn web_demo.app:app --host 0.0.0.0 --port 8088│ │
│  │  Healthcheck: curl /health (30s interval, 3 retries)      │ │
│  │  Volumes:                                                  │ │
│  │    ./logs:/app/logs          (uvicorn logs)               │ │
│  │    ./artifacts:/app/artifacts  (CSV runtime data)          │ │
│  │    ./.cache:/app/.cache      (embedding index)            │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Ollama (宿主机或独立容器, :11434)                         │ │
│  │  模型: bge-m3 (1.2GB)                                     │ │
│  │  Docker 内通过 host.docker.internal:11434 访问             │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Nginx (可选, :80/:443)                                   │ │
│  │  反向代理 → :8088                                         │ │
│  │  SSL: Let's Encrypt / 自签名证书                          │ │
│  │  Gzip: on                                                 │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

### 7.2 Docker Compose 配置

```yaml
services:
  web:
    build: .
    image: lab-safe-assistant:latest
    container_name: lab-safe-assistant
    restart: unless-stopped
    ports: ["${DEMO_PORT:-8088}:8088"]
    env_file: .env.web_demo
    environment:
      EMBEDDING_BACKEND: ollama
      EMBEDDING_MODEL: bge-m3
      ENABLE_EMBEDDING: "1"
      OLLAMA_BASE_URL: "http://host.docker.internal:11434"
    volumes:
      - ./logs:/app/logs
      - ./artifacts:/app/artifacts
      - ./.cache:/app/.cache
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://localhost:8088/health"]
      interval: 30s
      timeout: 10s
      start_period: 60s
      retries: 3
```

### 7.3 CI/CD

**GitHub Actions 工作流**（`.github/workflows/build-and-push-image.yml`）：

- **触发**：push 到 `main` 分支
- **构建**：`docker buildx build` 多架构（linux/amd64, linux/arm64）
- **推送**：`ghcr.io/leilehuimieba/lab-safety-assistant:latest`
- **缓存**：GitHub Actions cache + Docker layer cache

### 7.4 环境变量完整清单

| 变量 | 默认值 | 说明 |
|---|---|---|
| `DEMO_PORT` | 8088 | Web 服务端口 |
| `DIFY_API_BASE` | `http://127.0.0.1:8080` | Dify API 地址（可选） |
| `DIFY_APP_API_KEY` | — | Dify App API Key（可选，不配即跳过 Dify 链路） |
| `DIFY_TIMEOUT` | 120 | Dify 请求超时（秒） |
| `OPENAI_BASE_URL` | `http://ai.little100.cn:3000/v1` | LLM API 地址 |
| `OPENAI_API_KEY` | — | LLM API Key |
| `OPENAI_MODEL` | `gpt-5.2-codex` | 默认模型 |
| `FALLBACK_MODELS` | `grok-3-mini,grok-4,grok-3` | 模型 fallback 链 |
| `ENABLE_EMBEDDING` | `0` | 是否启用语义检索 |
| `EMBEDDING_BACKEND` | `sentence-transformers` | ollama / sentence-transformers |
| `EMBEDDING_MODEL` | `BAAI/bge-m3` | Embedding 模型名 |
| `EMBEDDING_DEVICE` | `cpu` | sentence-transformers 推理设备 |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API 地址 |
| `SEMANTIC_WEIGHT` | `12.0` | 知识库语义检索权重 |
| `EMERGENCY_SEMANTIC_WEIGHT` | `6.0` | 应急卡片语义检索权重 |
| `TRAINING_PASS_THRESHOLD` | `80` | 培训通过分数线 |

---

## 8. 测试策略

### 8.1 测试层次

| 层次 | 工具 | 覆盖范围 | 当前数量 |
|---|---|---|---|
| 单元测试 | pytest | services 层所有函数 | — |
| 集成测试 | pytest + FastAPI TestClient | 全部 API 端点 | — |
| 场景测试 | pytest | 端到端用户场景 | — |
| 数据完整性测试 | pytest | CSV 读写、字段校验、边界条件 | — |
| **合计** | **pytest** | **全部层次** | **157 项** |

### 8.2 测试环境配置

```python
# tests/conftest.py
os.environ.setdefault("ENABLE_EMBEDDING", "0")  # 测试环境默认禁用 embedding
```

禁用 embedding 的原因：
- CI 环境无 Ollama 服务
- sentence-transformers 首次下载 bge-m3 模型可能超时
- 纯文本检索模式足以覆盖检索逻辑和 fallback 测试

### 8.3 当前测试状态

- **总计**：157 项
- **通过**：155 项
- **失败**：2 项（`test_main_writes_clean_artifacts_and_manifest`, `test_fuzzy_metric_defaults_to_pass_when_no_fuzzy_rows` — 属于评测脚本相关）
- **目标**：157/157

### 8.4 MVP 场景测试重点

| 测试场景 | 验证要点 | API 端点 |
|---|---|---|
| 高风险阻断 | 输入高风险 + 缺关键项 → `allow_start=false` | `POST /api/checklist/submit` |
| 来源引用 | 问答返回非空 `citations` | `POST /api/chat` |
| 低置信队列 | 知识库外问题 → `low_confidence=true` + 写入 CSV | `POST /api/chat` |
| 老师审核 | approve/reject → 状态正确更新 | `PATCH /api/checklist/{id}/review` |
| 应急匹配 | 12 张卡片全部正确匹配 | `GET /api/emergency/match` |
| 培训评分 | 答对/答错评分准确 | `POST /api/training/submit` |
| 看板数据 | dashboard 返回正确统计数据 | `GET /api/admin/dashboard` |
| 事故 CRUD | 创建/查询/更新/删除全流程 | `GET/POST/PATCH/DELETE /api/incidents` |

---

## 9. 关键设计决策记录

### 决策 1：CSV 文件优先于 SQLite

**选择**：MVP 阶段使用 CSV/JSON 文件存储
**理由**：
- 当前数据量小（知识库 142 条，运行时记录百条级别）
- CSV 可用 Excel/WPS 直接打开编辑，非开发人员也可维护
- 无需 ORM、Migration、连接池管理
- 后续自然迁移路径明确：CSV → SQLite（第五阶段）→ PostgreSQL（产品化）
- pytest 可直接验证文件内容

### 决策 2：双路混合检索而非纯向量检索

**选择**：文本 token 匹配 + bge-m3 语义向量混合，加权融合
**理由**：
- **文本匹配精确**：关键词/编号查询不丢，适合 SOP 编号、化学品名称等精确查询
- **语义检索泛化**：同义词/变体不丢，如"盐酸"↔"HCl"、"着火"↔"起火"
- **独立降级**：Ollama 不可用时纯文本检索仍可工作，系统不崩溃
- **权重可调**：通过环境变量动态调整语义权重，无需改代码

### 决策 3：规则引擎在 LLM 前执行

**选择**：YAML 规则引擎在 LLM 调用前完成硬阻断判断
**理由**：
- 安全边界是**确定性**的（pattern match），不依赖 LLM 的 prompt compliance
- 规则文件可由非技术人员修改，改完即生效
- YAML 可读可版本管理，规则变更可追溯
- 减少 LLM 调用次数（硬阻断直接返回，不消耗 LLM 配额）

### 决策 4：Ollama bge-m3 作为默认 Embedding 后端

**选择**：Ollama API 调用 bge-m3，sentence-transformers 作为备选
**理由**：
- Ollama 提供 GPU 加速，推理速度远快于 CPU
- 不占用 Python 进程内存（1.2GB 模型在独立进程）
- sentence-transformers 提供离线备选，无网络时也可工作
- Docker 容器通过 `host.docker.internal` 可访问宿主机 Ollama
- 双后端通过 `EMBEDDING_BACKEND` 环境变量秒级切换

### 决策 5：Vite SPA 替换旧单页 HTML

**选择**：新前端使用 Vite 5 + TypeScript 5 + Tailwind CSS 3
**理由**：
- 旧单页 HTML 难以维护，8 个页面功能互相堆叠
- Vite 构建产物为纯静态文件（~30KB JS + ~10KB CSS gzipped），FastAPI 可直接 serve
- TypeScript 减少运行时类型错误
- Tailwind CSS JIT 编译，最终 CSS 仅包含实际使用的类
- SPA 客户端路由支持 8 个独立页面，FastAPI 只需一个 fallback 路由

---

## 10. 项目文件结构（完整）

```
lab-safe-assistant-github/                      # 项目根目录
│
├── web_demo/                                   # Web 应用主目录
│   ├── app.py                                  # FastAPI 入口 + 静态文件服务 + SPA fallback
│   ├── models.py                               # Pydantic 模型定义（324 行，30+ 模型）
│   ├── repositories.py                         # 数据访问层 + 路径常量 + 词典 + 缓存（436 行）
│   │
│   ├── routers/                                # API 路由层（7 个文件）
│   │   ├── __init__.py                         # 空（包声明由 app.py 直接导入）
│   │   ├── chat_routes.py                      # 问答 + Dify 代理（169 行）
│   │   ├── risk_routes.py                      # 风险评估 + 检查清单 + 老师审核（48 行）
│   │   ├── emergency_routes.py                 # 应急卡片匹配（30 行）
│   │   ├── training_routes.py                  # 培训考核 + 花名册管理（183 行）
│   │   ├── incident_routes.py                  # 事故管理 CRUD（47 行）
│   │   ├── admin_routes.py                     # 管理看板 + 导出 + 工作区状态（113 行）
│   │   └── meta_routes.py                      # 首页 + 健康检查 + 元信息（26 行）
│   │
│   ├── services/                               # 业务逻辑服务层（10 个文件）
│   │   ├── __init__.py                         # 统一导出接口
│   │   ├── kb_service.py                       # 混合检索 + 规则引擎匹配
│   │   ├── answer_service.py                   # 答案构建 + 低置信判断 + 入队
│   │   ├── risk_service.py                     # 风险评估 + 检查清单生成 + 提交审批（238 行）
│   │   ├── emergency_service.py                # 应急卡片混合匹配
│   │   ├── training_service.py                 # 题库管理 + 评分 + 统计
│   │   ├── incident_service.py                 # 事故 CRUD + 逾期/复发风险
│   │   ├── dashboard_service.py                # 管理看板聚合 + 周报 + CSV 导出
│   │   ├── upstream_service.py                 # LLM 调用封装（Dify + OpenAI-compatible）
│   │   ├── llm_output_service.py               # LLM 输出清洗 + 乱码修复
│   │   └── meta_service.py                     # 应用版本/评测/稳定性元信息
│   │
│   ├── data/                                   # 种子数据
│   │   ├── emergency_cards.json                # 12 张应急卡片（中英文双语）
│   │   └── training_question_bank.json         # 50 道培训题（10 类别）
│   │
│   ├── frontend/                               # Vite SPA 前端
│   │   ├── index.html                          # 入口 HTML
│   │   ├── package.json                        # pnpm 依赖
│   │   ├── tsconfig.json                       # TypeScript 配置
│   │   ├── vite.config.ts                      # Vite 配置（base: './'）
│   │   ├── tailwind.config.js                  # Tailwind 主题
│   │   ├── postcss.config.js                   # PostCSS
│   │   ├── src/                                # TypeScript 源码
│   │   │   ├── main.ts                         # 应用入口
│   │   │   ├── router.ts                       # 客户端路由
│   │   │   ├── types/                          # 类型定义（~20 文件）
│   │   │   ├── api/                            # API 请求层（~8 文件）
│   │   │   ├── store/                          # 状态管理
│   │   │   ├── components/                     # 可复用组件（~15 文件）
│   │   │   ├── pages/                          # 8 个页面组件
│   │   │   └── styles/                         # 全局样式
│   │   └── dist/                               # 构建产物（提交到 Git）
│   │       ├── index.html
│   │       └── assets/
│   │           ├── main-XXXXXXXX.js
│   │           └── main-XXXXXXXX.css
│   │
│   ├── templates/                              # 旧前端备份（历史）
│   │   └── index.html.bak_v82
│   │
│   ├── requirements.txt                        # web_demo 专用依赖
│   └── __init__.py
│
├── libs/                                       # 公共库（跨模块共享）
│   ├── common_io.py                            # CSV/JSON 通用读写
│   ├── text_utils.py                           # 文本标准化 + 分词 + Jaccard 相似度
│   ├── time_utils.py                           # 日期解析 + 天数判断
│   └── embedding_utils.py                      # bge-m3 语义向量引擎（~300 行）
│
├── scripts/                                    # 运维与自动化脚本
│   ├── start_web_demo_local.ps1                # 本地启动
│   ├── stop_web_demo_local.ps1                 # 本地停止
│   ├── status_web_demo_local.ps1               # 本地状态
│   ├── run_local_demo_via_server_dify.ps1      # SSH tunnel + 服务器 Dify
│   ├── run_v8_2_release.ps1                    # V8.2 一键发布
│   ├── eval_kb_retrieval.py                    # 检索质量评估
│   ├── quality_gate.py                         # 质量门禁
│   └── pipeline/                               # 数据入库流程脚本
│
├── tests/                                      # pytest 测试（157 项）
│   ├── conftest.py                             # 全局 fixture（含 ENABLE_EMBEDDING=0）
│   ├── test_web_demo_routes.py                 # API 路由测试
│   ├── test_eval_smoke.py                      # 评测冒烟测试
│   └── ...
│
├── docs/                                       # 项目文档
│   ├── README.md                               # 文档执行入口
│   ├── roadmap.md                              # 项目路线图
│   ├── product/                                # 产品文档
│   │   ├── prd_lab_safety_copilot_no_dify_20260428.md  # no-Dify PRD
│   │   ├── requirements_spec_20260429.md               # 需求规格说明书 ← 本文档对应用
│   │   └── design_spec_20260429.md                     # 系统设计文档 ← 本文档对应用
│   ├── changes/                                # Change 工作区
│   ├── ops/                                    # 运维文档
│   ├── eval/                                   # 评测文档
│   └── pipeline/                               # 入库流程文档
│
├── artifacts/                                  # 运行时数据（应用读写）
│   ├── checklists/checklist_runs.csv           # 检查清单运行记录
│   ├── training/
│   │   ├── training_attempts.csv               # 培训尝试记录
│   │   └── training_mistakes.csv               # 培训错题记录
│   ├── incidents/incident_reviews.csv          # 事故记录
│   └── low_confidence_followups/data_gap_queue.csv  # 低置信队列
│
├── .cache/                                     # 缓存（Docker volume 持久化）
│   ├── embedding/                              # 知识库 bge-m3 向量索引
│   └── embedding_emergency/                    # 应急卡片 bge-m3 向量索引
│
├── data_sources/                               # 数据源模板
│   └── training_roster_template.csv            # 花名册 CSV 模板
│
├── release_exports/                            # 历史发布包
│   └── v8.2/                                   # 当前演示基线
│
├── deploy/                                     # 部署配置
│   └── .env.web_demo.example                   # 环境变量模板
│
├── knowledge_base_curated.csv                  # 主知识库（142 条，16 字段）
├── safety_rules.yaml                           # 安全规则（24 条，4c/16h/3m/1l）
│
├── Dockerfile                                  # 多阶段构建
├── docker-compose.yml                          # Docker 一键部署
├── .dockerignore                               # Docker 构建排除
├── .github/workflows/build-and-push-image.yml  # CI/CD
├── requirements.txt                            # Python 依赖声明
├── pytest.ini                                  # pytest 配置
├── AGENTS.md                                   # AI Agent 协作规范
├── HANDOFF_PROMPT.md                           # 项目交接提示词
└── README.md                                   # 项目说明
```

---

## 11. 后续演进路径

### 短期（第二阶段联调完成后，2027H1）

1. **SQLite 替换 CSV**：常量定义 → `database.db`，使用 `sqlite3` 标准库
2. **Reranker 精排**：bge-reranker-v2-m3 在语义检索后二次排序，提升 Top-3 准确率
3. **检查清单模板管理**：支持老师自定义/追加检查项（JSON/YAML 可配置）

### 中期（试点反馈后，2027H2）

1. **用户认证**：简易 session-based 登录，按角色区分视图
2. **多课程数据隔离**：按课程/课题组维度切分看板和审核队列
3. **通知机制**：高风险新申请时 WebSocket/邮件通知老师
4. **知识库管理后台**：Web 界面增删改知识条目 + 自动补充低置信队列的快捷入口

### 长期（产品化，2028+）

1. **PostgreSQL 迁移**：多用户并发支持、连接池、事务
2. **SSO 集成**：对接学校 CAS / OAuth 统一认证
3. **Pipeline 自动化**：定时抓取公开安全资料（chemicalsafety.com 等），自动清洗入库
4. **数据分析与预警**：历史趋势分析、风险预测模型、培训效果追踪
5. **移动端适配**：PWA 或微信小程序版本

---

## 12. 版本历史

| 版本 | 日期 | 变更说明 |
|---|---|---|
| v1.0 | 2026-03 | v8.2 演示基线版本，基于 Dify 工作流 |
| v1.5 | 2026-04-28 | no-Dify 重定位初版设计 |
| v2.0 | 2026-04-29 | 完整设计文档，对齐申报书数据，补充全部模块细节 |
