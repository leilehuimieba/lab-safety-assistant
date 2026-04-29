# Lab Safety Copilot 系统设计文档

> 版本：v2.0
> 日期：2026-04-29
> 对应需求：`docs/product/requirements_spec_lab_safety_copilot_20260429.md`
> 当前阶段：Phase 5 — no-Dify 需求重定位与轻量 MVP

---

## 1. 设计概述

### 1.1 设计目标

基于需求规格说明书，设计 Lab Safety Copilot 的技术架构，达成以下目标：

1. **本地可运行**：不依赖 Dify 即可完成主链路演示
2. **轻量可测试**：pytest 全量回归，纯文本 fallback 确保无外部依赖时也可运行
3. **渐进可扩展**：模块化分层，后续可平滑迁移到 SQLite / Reranker / 本地 LLM
4. **快速迭代**：CSV/JSON 数据、YAML 规则、Vite SPA 热更新

### 1.2 设计原则

- **vibe coding 优先**：保持最小可用结构，不过度工程化
- **安全兜底优先**：失败时降级到安全结果，不吐危险答案
- **展示可复现优先**：演示链路可稳定复现，非演示功能容忍降级
- **数据可迁移**：CSV/JSON 格式，非私有二进制

### 1.3 技术选型

| 层面 | 选型 | 选型理由 |
|---|---|---|
| Web 框架 | FastAPI 0.115 | 异步支持、自动 OpenAPI、Pydantic 集成 |
| ASGI 服务器 | uvicorn 0.34 | 轻量、支持热重载 |
| 前端 | Vite 5 + TypeScript 5 + Tailwind CSS 3 | 快速构建、类型安全、原子化样式 |
| 数据存储 | CSV + JSON 文件 | MVP 阶段零依赖持久化 |
| 知识检索 | 文本 token 匹配 + bge-m3 语义向量 | 双路混合召回，可独立降级 |
| Embedding | Ollama (bge-m3) / sentence-transformers | 双后端，通过环境变量切换 |
| 安全规则 | YAML | 可读可编辑，非开发人员可维护 |
| LLM 调用 | OpenAI-compatible API 直连 | 通用协议，可切任意兼容服务 |
| 容器化 | Docker + docker-compose | 一键部署，环境一致性 |
| CI/CD | GitHub Actions | 多架构镜像构建推送到 ghcr.io |
| 测试 | pytest 8.x | 138 个用例全部通过 |

---

## 2. 系统架构

### 2.1 架构总览

```
┌──────────────────────────────────────────────────────┐
│                    浏览器 (SPA)                       │
│            Vite + TypeScript + Tailwind               │
│                 /  /checklist /emergency ...          │
└──────────────────────┬───────────────────────────────┘
                       │ HTTP REST API
┌──────────────────────┴───────────────────────────────┐
│                 FastAPI (web_demo/app.py)              │
│                                                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐ │
│  │ Routers  │ │ Routers  │ │ Routers  │ │ Routers │ │
│  │ chat     │ │ risk     │ │ training │ │ admin   │ │
│  │ emergency│ │ incident │ │ meta     │ │         │ │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬────┘ │
│       └──────────────┴────────────┴────────────┘      │
│                          │                            │
│  ┌───────────────────────┴────────────────────────┐  │
│  │              Services (业务逻辑层)               │  │
│  │  kb_service / risk_service / answer_service    │  │
│  │  training_service / incident_service           │  │
│  │  emergency_service / dashboard_service         │  │
│  │  upstream_service / meta_service               │  │
│  │  llm_output_service                           │  │
│  └───────────────────────┬────────────────────────┘  │
│                          │                            │
│  ┌───────────────────────┴────────────────────────┐  │
│  │            Data Layer (数据访问层)              │  │
│  │  repositories.py + libs/ (common_io,            │  │
│  │  text_utils, time_utils, embedding_utils)      │  │
│  └──────────────┬──────────────┬──────────────────┘  │
│                 │              │                      │
│  ┌──────────────┴──┐  ┌───────┴──────────┐          │
│  │ 本地文件系统     │  │ 外部服务          │          │
│  │ CSV / JSON /    │  │ Ollama / OpenAI  │          │
│  │ YAML / .cache   │  │ Compatible API   │          │
│  └─────────────────┘  └──────────────────┘          │
└──────────────────────────────────────────────────────┘
```

### 2.2 分层职责

| 层 | 文件 | 职责 |
|---|---|---|
| 路由层 | `web_demo/routers/*.py` | HTTP 请求解析、参数校验、响应序列化 |
| 服务层 | `web_demo/services/*.py` | 业务逻辑编排、规则评估、答案构建 |
| 数据层 | `web_demo/repositories.py` | 数据加载、缓存、路径常量、CSV 读写 |
| 公共库 | `libs/*.py` | 文本处理、时间工具、Embedding、通用 IO |
| 模型层 | `web_demo/models.py` | Pydantic 请求/响应模型定义 |

---

## 3. 模块设计

### 3.1 路由层

#### 3.1.1 Chat Router (`chat_routes.py`)

**路径**：`POST /api/chat`, `GET /api/search`
**核心流程**：

```
用户提问
  ↓
规则匹配 (match_rule)
  ↓
硬阻断判断 (should_enforce_terminal_rule)
  ├── refuse → 返回规则引擎答案（保守提示）
  ├── redirect_emergency → 引导至应急卡片
  └── ask_for_more_info → 反问缺失条件
  ↓
知识库检索 (retrieve_citations, top_k=4)
  ↓
低置信判断 (assess_low_confidence)
  ↓
LLM 调用 (call_dify_lab 或 call_upstream)
  ↓
失败 fallback (build_fallback_lab_answer)
  ↓
低置信入队 (append_low_confidence_followup)
  ↓
返回 ChatResponse
```

#### 3.1.2 Risk Router (`risk_routes.py`)

| 端点 | 方法 | 功能 |
|---|---|---|
| `/api/risk/assess` | POST | 风险评估（含别名 `/api/risk_assess`） |
| `/api/checklist/template` | POST | 生成检查清单模板 |
| `/api/checklist/submit` | POST | 提交检查清单结果 |
| `/api/checklist/{id}/review` | PATCH | 老师审核（approve/reject） |

#### 3.1.3 Training Router (`training_routes.py`)

| 端点 | 方法 | 功能 |
|---|---|---|
| `/api/training/questions` | GET | 获取随机题目 |
| `/api/training/submit` | POST | 提交答案并评分 |
| `/api/training/stats` | GET | 培训统计数据 |
| `/api/training/roster_status` | GET | 花名册完成状态 |
| `/api/training/roster_upload` | POST | 上传花名册 CSV |
| `/api/training/roster_template.csv` | GET | 下载花名册模板 |

#### 3.1.4 Emergency Router (`emergency_routes.py`)

| 端点 | 方法 | 功能 |
|---|---|---|
| `/api/emergency/cards` | GET | 获取全部应急卡片 |
| `/api/emergency/match` | GET/POST | 应急场景匹配 |

#### 3.1.5 Incident Router (`incident_routes.py`)

| 端点 | 方法 | 功能 |
|---|---|---|
| `/api/incidents` | GET | 事故列表（支持状态和逾期筛选） |
| `/api/incidents` | POST | 创建事故记录 |
| `/api/incidents/{id}` | PATCH | 更新事故记录（状态流转） |
| `/api/incidents/{id}` | DELETE | 删除事故记录 |

#### 3.1.6 Admin Router (`admin_routes.py`)

| 端点 | 方法 | 功能 |
|---|---|---|
| `/api/admin/dashboard` | GET | 管理看板数据 |
| `/api/admin/export.csv` | GET | 导出 CSV 报告 |
| `/api/admin/weekly_report.md` | GET | 导出 Markdown 周报 |
| `/api/workspace/status` | GET | 工作区运行状态 |

---

### 3.2 服务层

#### 3.2.1 KB Service (`kb_service.py`)

**职责**：知识库检索与安全规则匹配

```
retrieve_citations(query, top_k) → list[Citation]
  ├── 文本 token 匹配（Jaccard similarity on normalized tokens）
  ├── bge-m3 语义检索（当 ENABLE_EMBEDDING=1 时）
  └── 混合排序（SEMANTIC_WEIGHT 控制语义权重，默认 12.0）

match_rule(question) → dict | None
  ├── 遍历 safety_rules.yaml 的 patterns
  └── 检查 refine_intent_markers（REFUSE / EMERGENCY）

should_enforce_terminal_rule(question, rule) → bool
  └── 判断是否触发硬阻断 / 应急重定向 / 追问
```

**混合检索算法**：

```
final_score = text_score + SEMANTIC_WEIGHT × semantic_score
```

如果 Ollama 不可用，语义检索自动 fallback 到纯文本模式（不崩溃）。

#### 3.2.2 Answer Service (`answer_service.py`)

**职责**：答案构建、低置信判断、rule answer 生成

```
assess_low_confidence(citations) → (bool, str)
  └── top score < DEFAULT_LOW_CONFIDENCE_TOP_SCORE (3.5) → 低置信

build_rule_answer(rule, citations) → str
  └── 生成规则引擎的保守回答

build_fallback_lab_answer(question, citations, rule, low_confidence_reason) → str
  └── 结构化 fallback 回答（结论 → 步骤 → 禁止项 → 升级）

append_low_confidence_followup(...) → bool
  └── 低置信问题写入 data_gap_queue.csv
```

#### 3.2.3 Risk Service (`risk_service.py`)

**职责**：风险评估、检查清单生成、提交评估

```
build_risk_assessment(scenario, citations, rule) → RiskAssessResponse
  ├── 风险评分 = max(规则严重性评分, 知识库最高风险评分, 关键词评分)
  ├── 危险类型识别（HAZARD_HINTS 词典匹配）
  └── PPE 推荐（PPE_HINTS 词典匹配）

build_checklist_template(scenario) → ChecklistTemplateResponse
  ├── 基础检查项（6 项）
  ├── 危险类型专项（Chemical/Electrical/Fire/Cryogenic/Mechanical/Biosafety）
  └── 高风险追加（导师批准 + 单人操作管控）

evaluate_checklist_submission(payload) → ChecklistSubmitResponse
  ├── 关键项全部已勾选 → allow_start=true, 自动批准
  └── 有缺失关键项 → allow_start=false, pending 待审核
```

**风险评分矩阵**：

| 条件 | 分值贡献 |
|---|---|
| 规则严重性 critical | 5 |
| 规则严重性 high | 4 |
| 规则严重性 medium | 3 |
| 知识库最高风险评分 | 1-5 |
| 高危关键词（fire/shock/explosion/leak/burn/toxic） | 5 |
| 无高危关键词 | 3 |
| 最终评分 | max(以上)，clamp [1,5] |

#### 3.2.4 Training Service (`training_service.py`)

**职责**：题库管理、考核评分、统计

```
get_training_questions(limit) → list[dict]
  └── 从 JSON 题库随机抽取不重复题目

grade_training_submit(payload) → TrainingSubmitResponse
  ├── 逐题比对 selected_indices vs correct_indices
  ├── 计算总分和是否通过
  └── 写 CSV 记录（attempts + mistakes）

load_training_stats() → TrainingStatsResponse
  └── 汇总通过率、平均分、类别错误分布、近期成绩
```

#### 3.2.5 Emergency Service (`emergency_service.py`)

**职责**：应急卡片匹配

```
match_emergency_card(query) → EmergencyMatchResponse
  ├── bge-m3 语义检索（EMERGENCY_SEMANTIC_WEIGHT=6.0）
  └── 文本 token 匹配（fallback）
```

#### 3.2.6 Dashboard Service (`dashboard_service.py`)

**职责**：管理看板、工作区状态、周报生成、CSV 导出

```
load_admin_dashboard(days, risk_level, incident_status) → AdminDashboardResponse
  ├── metrics：检查单数、待审核数、培训统计
  ├── low_confidence_top：知识缺口排名
  ├── recent_high_risk_scenarios：高风险阻断记录
  └── incident_summary / overdue_incidents

build_workspace_status() → WorkspaceStatusResponse
  ├── Dify 连接状态
  ├── 知识库条数
  ├── 低置信队列数
  └── 类别/危险分布
```

#### 3.2.7 Upstream Service (`upstream_service.py`)

**职责**：LLM 调用封装

```
call_dify_lab(question) → (answer, model_name)
  └── Dify API 调用（可选链路）

call_upstream(mode, question, citations, guardrail) → (answer, model_name)
  └── OpenAI-compatible API 直连
```

---

### 3.3 数据层

#### 3.3.1 Repositories (`repositories.py`)

**路径常量**：

| 常量 | 路径 | 内容 |
|---|---|---|
| `KB_FILE` | `knowledge_base_curated.csv` | 主知识库 |
| `RULES_FILE` | `safety_rules.yaml` | 安全规则 |
| `EMERGENCY_CARDS_FILE` | `web_demo/data/emergency_cards.json` | 应急卡片 |
| `TRAINING_BANK_FILE` | `web_demo/data/training_question_bank.json` | 培训题库 |
| `LOW_CONFIDENCE_QUEUE_FILE` | `artifacts/low_confidence_followups/data_gap_queue.csv` | 低置信队列 |
| `CHECKLIST_RUNS_FILE` | `artifacts/checklists/checklist_runs.csv` | 检查单运行记录 |
| `TRAINING_ATTEMPTS_FILE` | `artifacts/training/training_attempts.csv` | 培训尝试记录 |
| `TRAINING_MISTAKES_FILE` | `artifacts/training/training_mistakes.csv` | 培训错题记录 |
| `INCIDENT_REVIEWS_FILE` | `artifacts/incidents/incident_reviews.csv` | 事故记录 |

**缓存策略**：

- 知识库条目：首次加载后全局缓存（`_KB_CACHE`），线程安全
- 安全规则：首次加载后全局缓存（`_RULES_CACHE`）
- 应急卡片/题库：首次加载后全局缓存
- Embedding 索引：持久化到 `.cache/embedding/`，下次启动秒级加载

#### 3.3.2 Common IO (`libs/common_io.py`)

- `read_csv(path)` / `write_csv(path, rows)` — CSV 读写
- `load_json_list(path)` — JSON 数组加载
- `write_csv_row(path, headers, row)` — 追加一行 CSV
- `safe_read_csv_rows(path)` — 安全读取（文件不存在返回空列表）

#### 3.3.3 Embedding Utils (`libs/embedding_utils.py`)

**双后端架构**：

```
Embedding Backend
├── sentence-transformers (HuggingFace BAAI/bge-m3)
│   ├── 优点：离线可用，无需外部服务
│   └── 缺点：首次下载 1.2GB，CPU 推理较慢
│
└── Ollama (本地 bge-m3)
    ├── 优点：GPU 加速，API 调用
    └── 缺点：需单独运行 ollama serve
```

**索引持久化**：
- 首次计算后 pickle 序列化到 `.cache/embedding/`
- 支持多数据集独立索引（`_index_states` 字典）
- 知识库和应急卡片各自独立缓存

**环境变量控制**：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `EMBEDDING_BACKEND` | `sentence-transformers` | 后端选择 |
| `EMBEDDING_MODEL` | `BAAI/bge-m3` | 模型名 |
| `ENABLE_EMBEDDING` | `0`（web_demo 默认） | 开关 |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 地址 |
| `SEMANTIC_WEIGHT` | `12.0` | 知识库语义权重 |
| `EMERGENCY_SEMANTIC_WEIGHT` | `6.0` | 应急语义权重 |

---

## 4. 数据模型

### 4.1 核心实体

```
ChatRequest
  ├── mode: "lab" | "agent"
  └── question: str (1-4000)

ChatResponse
  ├── answer: str
  ├── mode/model/decision: str
  ├── risk_level: str
  ├── matched_rule_id / matched_rule_action: str
  ├── low_confidence / low_confidence_reason / followup_logged: bool/str/bool
  └── citations: list[Citation]

Citation
  ├── kb_id / title / source_title / source_org / source_url: str
  ├── risk_level / snippet / score: str/str/float

RiskAssessResponse
  ├── scenario / risk_score / risk_level: str/int/str
  ├── key_hazards / ppe / forbidden / emergency_actions / recommended_steps: list[str]
  ├── low_confidence / low_confidence_reason: bool/str
  └── citations: list[Citation]

ChecklistTemplateResponse
  ├── scenario / risk_score / risk_level: str/int/str
  ├── key_hazards: list[str]
  ├── checklist: list[ChecklistItem]
  ├── recommended_actions: list[str]
  └── citations: list[Citation]

ChecklistItem
  ├── id / label: str
  ├── critical / checked: bool
  └── note: str

ChecklistSubmitResponse
  ├── record_id / submitted_at / scenario / operator: str
  ├── risk_score / risk_level: int/str
  ├── key_hazards: list[str]
  ├── allow_start: bool
  ├── blocking_reasons / next_actions: list[str]
  └── review_status / reviewed_by / reviewed_at / review_comment: str

EmergencyCard
  ├── id / title / category / summary: str
  ├── trigger_signs / immediate_actions / forbidden / ppe / escalation: list[str]

TrainingSessionResponse
  ├── session_id / total_questions / pass_threshold: str/int/int
  └── questions: list[TrainingQuestionPublic]

TrainingSubmitResponse
  ├── attempt_id / session_id / participant / submitted_at: str
  ├── score / total_questions / pass_threshold / passed: int/int/int/bool
  ├── weak_categories / recommended_actions: list[str]
  └── review: list[TrainingReviewItem]

IncidentRecord
  ├── incident_id / reported_at / updated_at / reporter / title / scenario: str
  ├── severity / status / location: str
  ├── cause_categories / immediate_actions / corrective_actions: list[str]
  ├── owner / due_date / closure_notes: str
  └── recurrence_risk / overdue / overdue_days: str/bool/int

AdminDashboardResponse
  ├── metrics: list[DashboardMetric]
  ├── low_confidence_top: list[DashboardLowConfidenceItem]
  ├── recent_high_risk_scenarios: list[DashboardHighRiskScenario]
  ├── incident_summary: dict[str, int]
  └── overdue_incidents: list[str]
```

### 4.2 数据流

#### 风险评估与开工检查完整数据流

```
POST /api/checklist/template {"scenario": "..."}
  │
  ├── retrieve_citations(scenario, top_k=5)
  │   ├── 文本检索（Jaccard token match）
  │   └── 语义检索（bge-m3 cosine similarity, 可选）
  │
  ├── match_rule(scenario)
  │   └── safety_rules.yaml pattern 匹配
  │
  ├── build_risk_assessment(scenario, citations, rule)
  │   ├── 风险评分 = max(规则严重性, 引用最高风险, 关键词)
  │   ├── 危险类型匹配（HAZARD_HINTS 词典）
  │   └── PPE 推荐（PPE_HINTS 词典）
  │
  └── build_checklist_template(scenario)
      ├── 基础 6 项 + 危险类型专项 + 高风险追加
      └── 去重 → ChecklistTemplateResponse

POST /api/checklist/submit {checklist items + operator}
  │
  ├── 重新生成模板（含所有检查项）
  ├── 比对提交项 vs 模板项
  ├── 收集未勾选的关键项 → blocking_reasons
  ├── allow_start = (len(blocking_reasons) == 0)
  ├── 写入 CHECKLIST_RUNS_FILE (CSV)
  └── 返回 ChecklistSubmitResponse
```

---

## 5. 前端设计

### 5.1 技术栈

| 技术 | 版本 | 用途 |
|---|---|---|
| Vite | 5.x | 构建工具 |
| TypeScript | 5.x | 类型安全 |
| Tailwind CSS | 3.x | 原子化样式 |
| PostCSS | 8.x | CSS 后处理 |

### 5.2 路由设计（SPA 客户端路由）

| 路径 | 页面 | 对应功能 |
|---|---|---|
| `/` | 首页 / 安全问答 | FR-01 |
| `/checklist` | 开工前检查 | FR-02, FR-03 |
| `/emergency` | 应急卡片 | FR-06 |
| `/training` | 培训考核 | FR-07 |
| `/teacher` | 老师审核工作台 | FR-04 |
| `/admin` | 管理看板 | FR-05 |
| `/incidents` | 事故管理 | FR-08 |
| `/status` | 系统状态 | - |

### 5.3 前端架构

```
web_demo/frontend/src/
├── main.ts           # 应用入口
├── router.ts         # Vue/React Router 或简易 Hash Router
├── api/              # API 调用封装
├── components/       # 可复用组件
├── pages/            # 页面组件
├── store/            # 状态管理（简易 reactive store）
├── types/            # TypeScript 类型定义
└── styles/           # 全局样式
```

### 5.4 静态资源服务

FastAPI 自定义 `/assets/{path:path}` 路由，强制返回正确 MIME 类型（解决 Windows Python mimetypes 对 `.js`/`.mjs` 识别问题）。

SPA fallback：所有非 `/api/`、非 `/assets/` 路径返回 `index.html`，由前端路由接管。

---

## 6. 部署架构

### 6.1 Docker 部署

```
┌─────────────────────────────────────────┐
│            Docker Host                    │
│                                           │
│  ┌─────────────────────────────────────┐ │
│  │  lab-safe-assistant (Python:3.13)    │ │
│  │  - FastAPI :8088                    │ │
│  │  - Volumes: logs, artifacts, .cache │ │
│  │  - Healthcheck: /health            │ │
│  └─────────────────────────────────────┘ │
│                                           │
│  ┌─────────────────────────────────────┐ │
│  │  Ollama (可选，独立容器或宿主机)     │ │
│  │  - API :11434                       │ │
│  │  - 模型: bge-m3 (1.2GB)            │ │
│  └─────────────────────────────────────┘ │
│                                           │
│  ┌─────────────────────────────────────┐ │
│  │  Nginx (可选，HTTPS 反向代理)       │ │
│  │  - :80 → :8088                     │ │
│  │  - :443 + SSL                      │ │
│  └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

### 6.2 Docker Compose 服务

```yaml
services:
  web:
    build: .
    ports: ["${DEMO_PORT:-8088}:8088"]
    env_file: .env.web_demo
    volumes: ["./logs:/app/logs", "./artifacts:/app/artifacts", "./.cache:/app/.cache"]
    healthcheck: /health

  # nginx: (可选)
```

### 6.3 CI/CD

GitHub Actions 工作流（`.github/workflows/build-and-push-image.yml`）：
- 触发条件：push 到 main 分支
- 构建多架构镜像：linux/amd64, linux/arm64
- 推送到：`ghcr.io/leilehuimieba/lab-safety-assistant`

### 6.4 环境变量完整清单

| 变量 | 默认值 | 说明 |
|---|---|---|
| `DEMO_PORT` | `8088` | 服务端口 |
| `DIFY_API_BASE` | `http://127.0.0.1:8080` | Dify API 地址（可选） |
| `DIFY_APP_API_KEY` | — | Dify App API Key（可选） |
| `DIFY_TIMEOUT` | `120` | Dify 请求超时（秒） |
| `OPENAI_BASE_URL` | `http://ai.little100.cn:3000/v1` | LLM API 地址 |
| `OPENAI_API_KEY` | — | LLM API Key |
| `OPENAI_MODEL` | `gpt-5.2-codex` | 默认模型 |
| `ENABLE_EMBEDDING` | `0` | 是否启用语义检索 |
| `EMBEDDING_BACKEND` | `sentence-transformers` | ollama / sentence-transformers |
| `EMBEDDING_MODEL` | `BAAI/bge-m3` | Embedding 模型名 |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API 地址 |
| `SEMANTIC_WEIGHT` | `12.0` | 知识库语义权重 |
| `EMERGENCY_SEMANTIC_WEIGHT` | `6.0` | 应急语义权重 |
| `TRAINING_PASS_THRESHOLD` | `80` | 培训通过分数 |

---

## 7. 安全设计

### 7.1 安全问答防护链

```
用户输入
  ↓
规则引擎硬阻断（refuse patterns）
  ├── "能不能绕过XX" → 拒绝回答
  ├── "可以倒下水道吗" → 拒绝回答
  └── "不戴手套可以吗" → 拒绝回答
  ↓
应急意图重定向（emergency patterns）
  ├── "着火了怎么办" → 引导应急卡片
  └── "受伤了怎么处理" → 引导应急卡片
  ↓
低置信度兜底
  └── top_score < 3.5 → 标记低置信，提示联系老师
  ↓
LLM 输出安全清洗 (sanitize_llm_output)
  └── 乱码修复 (fix_mojibake_text)
```

### 7.2 风险阻断链

```
实验场景输入
  ↓
风险评分 ≥ 4 (High/Critical) → 强制高风险检查项
  ↓
学生提交检查单
  ├── 全部关键项已勾选 → allow_start=true
  └── 任一关键项未勾选 → allow_start=false, review_status=pending
      ↓
      老师工作台显示待审核记录
```

---

## 8. 测试策略

### 8.1 测试层次

| 层次 | 工具 | 覆盖目标 |
|---|---|---|
| 单元测试 | pytest | services 层所有函数 |
| 集成测试 | pytest + FastAPI TestClient | API 端点全量回归 |
| 场景测试 | pytest | 端到端用户场景验证 |
| 浏览器走查 | 人工 | SPA 页面功能验证 |

### 8.2 当前测试状态

- pytest：138/138 通过
- 测试环境默认禁用 embedding（`ENABLE_EMBEDDING=0`）避免 CI 超时
- 测试数据独立于运行数据

### 8.3 MVP 测试重点

| 测试场景 | 验证要点 |
|---|---|
| 高风险阻断 | 输入高风险 + 缺关键项 → allow_start=false |
| 来源引用 | 安全问答返回非空 citations |
| 低置信队列 | 知识库外问题 → low_confidence=true, 入队 |
| 老师审核 | approve/reject 操作正常 |
| 应急匹配 | 4 张卡片全部正确匹配 |
| 培训评分 | 正确/错误答案评分准确 |

---

## 9. 关键设计决策记录

### 决策 1：CSV 优先而非 SQLite

**选择**：MVP 阶段使用 CSV/JSON 文件存储
**理由**：
- 当前数据量小（知识库 398 条，运行时记录量级在百条）
- CSV 可直接用 Excel 打开编辑，方便非开发人员维护
- 无需 ORM、迁移、连接管理
- 后续自然迁移路径明确（SQLite → PostgreSQL）

### 决策 2：双路混合检索而非纯向量检索

**选择**：文本 token 匹配 + bge-m3 语义向量混合
**理由**：
- 文本匹配精确（关键词/编号查询不丢），语义检索泛化（同义词/变体不丢）
- 语义检索可降级（Ollama 不可用时纯文本仍工作）
- 两路互补而非替代

### 决策 3：Dify 降级为可选而非完全移除

**选择**：保留 Dify 代理路由和调用逻辑，通过配置开关控制
**理由**：
- v8.2 演示链路已验证 Dify workflow 可用
- 不需要时可以完全忽略（不配 API Key 即跳过）
- 提供 fallback 选择（本地 fallback 答案 + OpenAI 直连）

### 决策 4：Vite SPA 替换旧单页 HTML

**选择**：新前端使用 Vite + TypeScript + Tailwind CSS
**理由**：
- 旧单页 HTML 难以维护，8 个页面功能互相堆叠
- Vite 构建产物为纯静态文件，FastAPI 可直接 serve
- TypeScript 减少运行时错误
- Tailwind CSS 快速出 UI，无需单独 CSS 文件

### 决策 5：Ollama 作为默认 Embedding 后端

**选择**：生产使用 Ollama bge-m3，sentence-transformers 作为备选
**理由**：
- Ollama 提供 GPU 加速，不占用 Python 进程内存
- sentence-transformers 首次下载慢（1.2GB）且在 Windows 上不稳定
- 双后端通过环境变量秒级切换
- Docker 容器可通过 `host.docker.internal` 访问宿主机 Ollama

---

## 10. 项目文件结构（当前）

```
lab-safe-assistant-github/
├── web_demo/                       # Web 应用
│   ├── app.py                      # FastAPI 入口 + 静态文件路由
│   ├── models.py                   # Pydantic 模型（323 行）
│   ├── repositories.py             # 数据访问层 + 常量（436 行）
│   ├── routers/                    # API 路由
│   │   ├── chat_routes.py          # 问答 + Dify 代理
│   │   ├── risk_routes.py          # 风险评估 + 检查清单
│   │   ├── emergency_routes.py     # 应急卡片
│   │   ├── training_routes.py      # 培训考核 + 花名册
│   │   ├── incident_routes.py      # 事故复盘
│   │   ├── admin_routes.py         # 管理看板 + 导出
│   │   └── meta_routes.py          # 健康检查 + 元信息
│   ├── services/                   # 业务逻辑
│   │   ├── kb_service.py           # 知识检索 + 规则匹配
│   │   ├── answer_service.py       # 答案构建 + 低置信处理
│   │   ├── risk_service.py         # 风险评估 + 检查清单
│   │   ├── emergency_service.py    # 应急卡片匹配
│   │   ├── training_service.py     # 培训考核
│   │   ├── incident_service.py     # 事故管理
│   │   ├── dashboard_service.py    # 看板 + 周报
│   │   ├── upstream_service.py     # LLM 调用
│   │   ├── llm_output_service.py   # LLM 输出清洗
│   │   └── meta_service.py         # 应用元信息
│   ├── data/                       # 种子数据
│   │   ├── emergency_cards.json
│   │   └── training_question_bank.json
│   └── frontend/                   # Vite SPA
│       ├── src/                    # TypeScript 源码
│       └── dist/                   # 构建产物
├── libs/                           # 公共库
│   ├── common_io.py                # CSV/JSON 读写
│   ├── text_utils.py               # 文本标准化、分词
│   ├── time_utils.py               # 时间解析、天数计算
│   └── embedding_utils.py          # bge-m3 语义检索
├── scripts/                        # 运维脚本
├── tests/                          # pytest 测试
├── docs/                           # 文档
│   ├── product/                    # 产品文档（PRD + 需求 + 设计）
│   ├── changes/                    # change 工作区
│   ├── ops/                        # 运维文档
│   ├── eval/                       # 评测文档
│   └── pipeline/                   # 入库流程文档
├── artifacts/                      # 运行时数据（应用生成）
├── knowledge_base_curated.csv      # 主知识库（398 条）
├── safety_rules.yaml               # 安全规则
├── Dockerfile                      # 多阶段构建
├── docker-compose.yml              # 一键部署
└── requirements.txt                # Python 依赖
```

---

## 11. 后续演进路径

### 短期（MVP 完成后）

1. **SQLite 迁移**：CSV → SQLite，支持并发写入和索引查询
2. **Reranker 精排**：bge-reranker 在语义检索后二次排序
3. **本地 LLM 接入**：支持 Ollama 本地模型作为 LLM 后端
4. **检查清单模板扩展**：支持老师自定义检查项

### 中期（试点反馈后）

1. **用户认证**：简易 JWT 或 session-based 登录
2. **多实验室支持**：按实验室/课题组隔离数据
3. **通知机制**：高风险新申请时通知老师
4. **知识库管理后台**：Web 界面增删改知识条目

### 长期（产品化）

1. **PostgreSQL 迁移**：多用户并发支持
2. **SSO 集成**：对接学校统一认证
3. **Pipeline 自动化**：定时抓取公开安全资料入库
4. **数据分析**：历史趋势、风险预测、培训效果评估
