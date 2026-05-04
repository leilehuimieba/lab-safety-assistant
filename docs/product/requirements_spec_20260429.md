# 实验安全前置哨 — 需求规格说明书

> **项目正式名称**：实验安全前置哨 —— 基于规则引擎与知识检索的实验前安全决策系统
> **产品代号**：Lab Safety Copilot / 实验前安全检查助手
> **文档版本**：v2.0
> **日期**：2026-04-29
> **对应申报书**：五邑大学大学生创新训练计划项目（2026版），省级创新训练项目
> **适用仓库**：`D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github`

---

## 1. 文档概述

### 1.1 文档目的

本文档是"实验安全前置哨"项目的完整需求规格说明，定义系统全部功能需求、非功能需求、用户角色、业务场景、数据需求和验收标准，作为后续设计、开发、测试和结题验收的统一依据。

### 1.2 项目基本信息

| 条目 | 内容 |
|---|---|
| 项目全称 | 实验安全前置哨 —— 基于规则引擎与知识检索的实验前安全决策系统 |
| 项目类别 | 一般项目 |
| 项目类型 | 创新训练项目 |
| 申报级别 | 省级 |
| 负责人 | 鲍梓濠 |
| 指导教师 | 龙华秋（网络工程师 / CISP） |
| 所属学院 | 电子与信息工程学院 |
| 实施周期 | 2026 年 6 月 — 2028 年 6 月（共 2 年） |
| 所属专业 | 电子与信息工程学院 |

### 1.3 术语定义

| 术语 | 英文 | 说明 |
|---|---|---|
| 开工前检查 | Pre-Operation Checklist | 实验开始前，学生对安全条件进行的自查流程 |
| 硬阻断 | Hard Block | 匹配到高危规则模式时，系统判定为暂不可开工 |
| 阻断原因 | Blocking Reason | 未满足的关键安全条件清单 |
| 三色决策卡 | Tri-Color Decision Card | 绿（可开工）/ 黄（需老师确认）/ 红（暂不可开工）的视觉化决策输出 |
| 老师审核包 | Teacher Review Package | 高风险实验的结构化摘要，含风险项、缺失项、系统建议 |
| 低置信队列 | Low-Confidence Queue | 系统无法可靠回答、需人工补充知识的问题集合 |
| 来源引用 | Source Citation | 回答中标注知识来源（来源单位、文件、链接） |
| 规则引擎 | Rule Engine | 基于 YAML 配置的确定性安全规则匹配系统，在 LLM 调用前执行 |
| 混合检索 | Hybrid Retrieval | 文本 token 匹配 + bge-m3 语义向量的双路检索融合 |

---

## 2. 产品定位

### 2.1 核心问题

当前高校实验室安全管理主要依赖三个方向：

1. **安全培训与考试系统** — 学生通过线上考试证明已学习安全知识
2. **综合 EHS 管理平台** — 面向管理者的台账、检查、隐患上报系统
3. **AI 安全问答** — 基于大语言模型的通用安全知识问答

三者的共同问题：**它们解决了"知不知道"和"事后记没记"，但没有解决"开不开工"这一最关键的即时决策问题。**

### 2.2 产品定义

本项目构建一个**轻量级的实验前安全决策系统**，将实验室安全检查从"事后合规"前移到"事前决策"。

**核心工作流**：

```text
学生在实验室准备开工
  → 输入实验内容（名称、试剂、设备、步骤）
  → 独立 YAML 规则引擎 + 本地知识库混合检索
  → 自动识别风险、生成检查清单
  → 输出结构化判断结论（可开工 / 需老师确认 / 暂不可开工）
  → 高风险事项推送老师工作台审核闭环
```

整个过程在 **1-2 分钟**内完成，所有决策留痕可追溯。

### 2.3 核心价值主张

| 维度 | 现有方案 | 本项目 |
|---|---|---|
| 时间节点 | 事后合规、事前告知 | **事前即时决策** |
| 决策形式 | 文字描述、需自行判断 | **结构化三色决策卡（红/黄/绿）** |
| 安全边界 | 依赖 prompt 约束（可被绕过） | **独立规则引擎确定性匹配** |
| 责任归属 | AI 黑盒判断 | **人机协同（AI 预处理，人做最终判断）** |
| 知识演进 | 静态知识库 | **低置信队列驱动持续补充** |
| 部署门槛 | 需对接学校系统 | **Docker 一键部署，单机运行** |

### 2.4 项目意义（四点）

1. **首次将"事前阻断"机制引入高校实验室安全管理**：弥补现有系统的核心空白——现有方案只管"知不知道"和"事后记没记"，本项目管"开不开工"
2. **采用独立规则引擎确保安全边界的确定性**：不依赖大模型 prompt 的不可靠约束，安全判断具有可解释性和可审计性
3. **通过人机协同决策闭环**：AI 预处理、人做最终判断，在不增加老师负担的前提下提升安全管理的覆盖面和可追溯性，审核一个实验不超过 30 秒
4. **系统不依赖特定商业平台**：Docker 一键部署，单台服务器即可运行，不需要对接学校信息化系统，单门课程即可试点

### 2.5 项目创新点

| 创新点 | 说明 |
|---|---|
| **事前阻断** | 首次将"事前阻断"逻辑引入高校实验安全场景，从"事后填表"变为"事前决策" |
| **独立规则引擎** | YAML 规则在 LLM 调用前执行硬阻断，安全边界不依赖 prompt，确定性可审计 |
| **结构化决策输出** | API 返回 allow_start / blocking_reasons / review_status 等结构化字段，非纯文本 |
| **低置信闭环** | 知识盲区自动入队、按频率排序、驱动定向补充，知识库从静态变自我进化 |
| **零平台依赖** | Docker 一键部署，不绑定特定 LLM 平台或学校信息化系统，单课程即可试点 |

### 2.6 不做范围（MVP 阶段）

- 不做完整 EHS 平台（不替代全校安全管理系统）
- 不做全量危化品库存管理
- 不做采购审批、门禁联动、IoT 实时监控
- 不做正式 SSO / 全校组织架构
- 不让 AI 直接承担最终安全许可责任
- 不强制接入任何特定商业平台或低代码平台

---

## 3. 用户角色

### 3.1 角色定义

| 角色 | 代号 | 核心诉求 | 使用频率 |
|---|---|---|---|
| 学生 / 新进实验人员 | STUDENT | 开工前快速判断实验是否安全、知道该检查什么、是否需要问老师 | 每次实验课前 |
| 教师 / 实验室负责人 | TEACHER | 审核高风险实验开工申请、查看培训完成情况、掌握学生安全盲区 | 每日 |
| 实验室管理员 / 安全员 | ADMIN | 全局安全状况总览、识别知识盲区和培训薄弱点、导出周报/报告 | 每周 |
| 系统维护人员 | MAINTAINER | 更新知识库和规则文件、监控检索质量、管理评测与发布 | 按需 |

### 3.2 角色详细描述

#### STUDENT（学生 / 新进实验人员）

**典型画像**：大二至大四本科生，有一定的实验操作经验但安全规范意识参差不齐。

**痛点**：
- 不知道实验前该检查什么，SOP/SDS 冗长不愿细看
- 不确定自己准备的条件是否充分（PPE 穿什么、通风开不开、废液倒哪里）
- 不确定哪些是绝对禁止的，哪些是可以自己判断的
- 出现不确定情况时不知道是否必须问老师，还是可以自行决定
- 发生意外时（溅到眼睛、起火、触电）不知道该怎么做第一步

**核心需要**：
- ① 输入实验信息 → 获得清晰的风险等级和"能/不能做"的判断
- ② 获得可逐项勾选的开工检查清单
- ③ 明确知道是否需要老师确认
- ④ 遇到事故时能看到清晰的处置步骤（应急卡片）

#### TEACHER（教师 / 实验室负责人）

**典型画像**：负责 1-3 门实验课程的教师或课题组负责人，同时指导多名学生。

**痛点**：
- 每学期重复提醒学生安全注意事项，口头传达覆盖不全
- 高风险实验缺少统一的审核视图，逐人检查效率低
- 学生是否真的理解了风险，无法客观衡量
- 缺少轻量的审核留痕记录（出事后无法证明"我当时确实提醒过"）

**核心需要**：
- ① 查看待审核的高风险实验列表
- ② 看到高风险摘要（风险是什么、缺失了什么、系统建议是什么）
- ③ 快速一键批准/驳回，并可附加文字说明
- ④ 导出记录用于教学管理

#### ADMIN（实验室管理员 / 安全员）

**典型画像**：学院或实验中心的安全管理员，负责整体安全运行和向上汇报。

**痛点**：
- 安全相关资料（SDS、SOP、事故记录、培训记录）分散在不同地方
- 学生提出的"奇怪安全疑问"无人沉淀，同样问题反复出现
- 高风险实验场景的分布和阻断原因缺少统计
- 培训和实际操作之间存在脱节

**核心需要**：
- ① 查看安全运行看板总览（高风险实验数量、阻断原因分布、培训通过率）
- ② 查看低置信问题队列，按频率排序识别最急需补充的知识盲区
- ③ 发现缺失的 SOP/SDS 或培训薄弱类别
- ④ 导出 Markdown 周报 / CSV 数据

---

## 4. 功能需求

### 4.1 功能全景

系统包含 9 大功能模块，当前全部已完成核心代码开发：

```
┌──────────────────────────────────────────────────────────────────┐
│                    实验安全前置哨 (Lab Safety Copilot)              │
├─────────────┬─────────────┬─────────────┬────────────────────────┤
│ 安全问答     │ 风险评估     │ 开工检查     │ 应急卡片（12张）         │
│ FR-01       │ FR-02       │ FR-03       │ FR-06                  │
│ 1148条知识库 │ 5级风险评分   │ 6+6+2检查项  │ 口语化匹配              │
├─────────────┼─────────────┼─────────────┼────────────────────────┤
│ 培训考核     │ 老师审核     │ 管理看板     │ 事故复盘                │
│ FR-07       │ FR-04       │ FR-05       │ FR-08                  │
│ 50题10类别   │ 一键批准/驳回  │ 6维度展示     │ 全生命周期管理          │
├─────────────┴─────────────┴─────────────┴────────────────────────┤
│                    低置信队列 & 知识管理 (FR-09)                    │
└──────────────────────────────────────────────────────────────────┘
```

### 4.2 功能需求详细说明

---

#### FR-01：安全问答

**优先级**：P0（已完成）
**所属角色**：STUDENT, TEACHER, ADMIN
**对应 API**：`POST /api/chat`, `GET /api/search`

**功能描述**：
用户通过自然语言提出实验室安全问题（中英文均可），系统从本地知识库混合检索相关条目，经规则引擎过滤后返回带来源引用的答案。

**输入规格**：

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| mode | string | "lab" 或 "agent" | lab = 正式安全问答（含检索+规则）；agent = 通用助手 |
| question | string | 1-4000 字符 | 用户的安全问题 |

**处理流程**（六步链路）：

```
Step 1 - 文本预处理
  用户问题 → normalize_search_text（小写化、去标点、中文分词混合）
  ↓
Step 2 - 规则引擎优先匹配
  match_rule(question) → 遍历 24 条 YAML 规则 patterns
  ├── 命中 refuse → 硬阻断，直接返回保守回答（不调用 LLM）
  ├── 命中 redirect_emergency → 重定向应急卡片
  ├── 命中 ask_for_more_info → 反问缺失条件
  └── 未命中 → 继续
  ↓
Step 3 - 知识库混合检索
  retrieve_citations(question, top_k=4)
  ├── 文本 token 匹配（Jaccard similarity on normalized tokens）
  ├── bge-m3 语义向量检索（ENABLE_EMBEDDING=1 时启用）
  └── 混合排序：final_score = text_score + 12.0 × semantic_score
  ↓
Step 4 - 低置信度判断
  assess_low_confidence(citations)
  └── top_score < 3.5 → low_confidence=true
  ↓
Step 5 - LLM 调用 / Fallback
  try: call_dify_lab(question)  或  call_upstream(mode, ...)
  except: build_fallback_lab_answer(question, citations, rule)
  ↓
Step 6 - 低置信入队 + 输出
  low_confidence → 写入低置信队列 CSV
  → 返回 ChatResponse
```

**输出规格**：

| 字段 | 类型 | 说明 |
|---|---|---|
| answer | string | 回答正文（Markdown 格式） |
| mode | string | 实际使用的模式 |
| model | string | 模型标识（如 "rule-engine" / "fallback-rule-engine" / LLM 名称） |
| decision | string | 决策标签（见下表） |
| risk_level | string | Low / Medium-Low / Medium / High / Critical |
| matched_rule_id | string | 匹配到的规则 ID（如 "R-006"） |
| matched_rule_action | string | refuse / redirect_emergency / ask_for_more_info / safe_answer |
| low_confidence | bool | 是否低置信 |
| low_confidence_reason | string | 低置信原因文本 |
| followup_logged | bool | 是否已写入低置信队列 |
| citations | Citation[] | 知识来源引用列表 |

**决策标签枚举**：

| 决策值 | 含义 | 触发条件 |
|---|---|---|
| rule_blocked | 规则硬阻断 | refuse action 命中 |
| emergency_redirect | 应急重定向 | redirect_emergency action 命中 |
| need_more_info | 需补充信息 | ask_for_more_info action 命中 |
| llm_answer | 正常 LLM 回答 | 无规则命中，正常检索+LLM |
| llm_answer_guarded | 带护栏的 LLM 回答 | 有规则命中但不触发硬阻断 |
| llm_low_confidence | 低置信 LLM 回答 | 检索分数低于阈值 |
| llm_fallback_structured | 结构化 fallback | LLM 调用失败时的兜底 |

**验收标准**：

| 标准 | 目标值 | 验证方法 |
|---|---|---|
| 硬阻断准确率 | 高危问题 100% 拦截 | 用 24 条规则的触发词测试，确认 refuse 动作无漏过 |
| 应急重定向准确率 | 应急场景 100% 引导 | 输入"着火了怎么办"→ 返回 redirect_emergency |
| 来源引用覆盖率 | 专业问答 ≥ 90% | 统计回答中 citations 非空的比例 |
| 低置信兜底率 | 知识不足时 100% 标记 | 输入知识库外问题 → low_confidence=true |
| 检索响应时间 | < 2s（纯文本）/ < 5s（含语义） | 本地性能测试 |
| 危险答案放行数 | 0 | 人工抽检 100 题，无可被利用的危险操作指导 |

---

#### FR-02：风险评估

**优先级**：P0（已完成）
**所属角色**：STUDENT
**对应 API**：`POST /api/risk/assess`, `POST /api/risk_assess`（别名）

**功能描述**：
用户输入实验场景描述，系统综合规则严重性、知识库引用风险等级和关键词分析，输出 1-5 级风险评分、危险类型标签、PPE 推荐和处置建议。

**输入**：scenario（string, 1-6000 字符）— 实验场景描述

**风险评分算法**：

```
risk_score = max(
    severity_score,   # 规则引擎匹配到的严重性映射：critical=5, high=4, medium=3, low=2
    citation_score,   # 知识库引用的最高风险等级数字
    keyword_score     # 高危关键词检测：含 fire/shock/explosion/leak/burn/toxic → 5, 否则 3
)
clamp(risk_score, 1, 5)
```

**危险类型识别**：基于 HAZARD_HINTS 词典（6 大类）：

| 危险类型 | 匹配关键词示例 |
|---|---|
| Chemical | acid, base, solvent, corrosive, 酸, 碱, 溶剂, 腐蚀, 危化品, 氧化剂, 易燃 |
| Biosafety | bio, pathogen, sample, 生物, 病原, 样本, 灭菌, 培养, 血液 |
| Electrical | electric, shock, battery, 触电, 带电, 高压, 电路, 电池 |
| Fire | fire, smoke, ignition, flammable, 火, 起火, 冒烟, 回流, 易燃 |
| Cryogenic | liquid nitrogen, cryogenic, 液氮, 深冷, 冻伤, 杜瓦 |
| Mechanical | centrifuge, rotation, 离心机, 旋转, 夹伤, 运动部件 |

**PPE 推荐**：基于 PPE_HINTS 词典（7 类）：Splash goggles, Face shield, Chemical resistant gloves, Lab coat, Respiratory protection, Cryogenic gloves, Electrical gloves

**输出**：

| 字段 | 类型 | 说明 |
|---|---|---|
| scenario | string | 原始场景描述 |
| risk_score | int | 1-5 风险评分 |
| risk_level | string | Low / Medium-Low / Medium / High / Critical |
| key_hazards | string[] | 识别到的危险类型列表 |
| ppe | string[] | 推荐 PPE 列表 |
| forbidden | string[] | 禁止事项（通用 + 专项） |
| emergency_actions | string[] | 应急处置步骤 |
| recommended_steps | string[] | 推荐操作步骤 |
| low_confidence / low_confidence_reason | bool/string | 低置信标记 |
| citations | Citation[] | 相关知识来源 |

**验收标准**：

| 标准 | 目标值 |
|---|---|
| 危险类型识别准确率 | ≥ 85% |
| 高危场景风险等级 | 输入"锂电池拆解"→ 返回 High 或 Critical |
| 中低危场景风险等级 | 输入"pH 试纸测自来水"→ 返回 Low 或 Medium-Low |

---

#### FR-03：开工前检查清单

**优先级**：P0（已完成）
**所属角色**：STUDENT
**对应 API**：`POST /api/checklist/template`, `POST /api/checklist/submit`

**功能描述**：
系统根据风险评估结果动态生成个性化开工检查清单。学生逐项勾选确认后提交，系统自动判定是否允许开工，高风险/缺失项推送老师审核。

**3.1 清单生成**

基础检查项（6 项，所有实验必须）：

| 检查项 ID | 内容 | Critical |
|---|---|---|
| sop_reviewed | SOP、SDS、实验目的已阅读并理解 | ✅ |
| label_verified | 试剂名称、浓度、标签已二次核对 | ✅ |
| ppe_ready | 所需 PPE 已就绪、正确穿戴、适用本任务 | ✅ |
| containment_ready | 通风、防护屏蔽、围堵措施到位且正常工作 | ✅ |
| emergency_ready | 应急喷淋、洗眼器、灭火器、逃生通道、紧急联系方式已确认 | ✅ |
| waste_route_ready | 废液分类和暂存路径在开工前已确认 | ❌ |

危险类型专项检查项（按危险类型自动追加，6 类各 1 项，均为 Critical）：

| 危险类型 | 专项检查项 |
|---|---|
| Chemical | 化学品不相容性、二次容器和防漏托盘已确认 |
| Biosafety | 生物安全柜、消毒剂和暴露途径控制已就绪 |
| Electrical | 接地、绝缘和断电隔离条件已确认 |
| Fire | 点火源已受控，适用灭火器在伸手可及范围内 |
| Cryogenic | 排气路径、面部防护和缺氧风险控制已确认 |
| Mechanical | 防护罩、动平衡和运动部件间隙已检查 |

高风险追加检查项（risk_score ≥ 4 时追加，2 项，均为 Critical）：

| 检查项 ID | 内容 |
|---|---|
| high_risk_authorized | 导师批准或双人核对已完成 |
| working_alone_control | 非单人操作，或已获批的升级路径有效 |

**3.2 提交与阻断判定**

提交时系统重新生成完整清单并逐项比对：

```
for each item in template.checklist:
    if item.critical AND NOT item.checked:
        → blocking_reasons.append(item.label)

allow_start = (len(blocking_reasons) == 0)
initial_review_status = "pending" if blocking else "approved"
```

阻断原因直接映射到具体检查项，学生知道该补什么。

**3.3 提交记录持久化**

每次提交写入 `artifacts/checklists/checklist_runs.csv`，包含 16 个字段：record_id、submitted_at、operator、scenario、risk_score、risk_level、key_hazards、allow_start、blocking_reasons、items_json（完整勾选状态）、notes、review_status、reviewed_by、reviewed_at、review_comment。

**输出**：

| 字段 | 说明 |
|---|---|
| record_id | 唯一记录 ID，格式 CHK-YYYYMMDD-XXXXXXXX |
| allow_start | true/false |
| blocking_reasons | 未满足的关键检查项列表 |
| next_actions | 下一步操作建议 |
| review_status | pending（待审核）/ approved（已通过） |

**验收标准**：

| 标准 | 目标值 |
|---|---|
| 基础检查项完整性 | 始终包含 6 项基础检查 |
| 危险类型专项 | 6 种危险类型各 1 项，正确匹配 |
| 高风险追加 | risk_score ≥ 4 时追加 2 项 |
| 关键项全部未勾选 → 阻断 | allow_start=false, blocking_reasons 非空 |
| 全部关键项已勾选 → 通过 | allow_start=true, review_status=approved |
| 阻断原因可读性 | 每条阻断原因直接对应检查项原文 |

---

#### FR-04：老师审核

**优先级**：P0（已完成）
**所属角色**：TEACHER
**对应 API**：`PATCH /api/checklist/{record_id}/review`

**功能描述**：
高风险事项自动推送至老师工作台。老师查看结构化的审核摘要，可一键批准或驳回，驳回时附带评语。完整的审核状态机记录在 CSV 中。

**审核状态机**：

```
pending ──→ approved  (老师批准)
pending ──→ rejected  (老师驳回，附评语)
```

**审核输入**：

| 字段 | 约束 | 说明 |
|---|---|---|
| action | "approve" 或 "reject" | 审核操作 |
| reviewer | string, max 120 | 审核人姓名，默认 "teacher" |
| comment | string, max 1000 | 审核评语 |

**验收标准**：

| 标准 | 目标值 |
|---|---|
| 审核信息完整度 | 摘要包含风险等级、缺失项、系统建议，老师 30 秒内看懂 |
| 操作即时性 | 批准/驳回即时写入 CSV，后续查询可见 |
| 评语附带 | 驳回时可附带文字说明原因 |
| 审核证据链 | CSV 记录包含 review_status / reviewed_by / reviewed_at / review_comment 四字段 |

---

#### FR-05：管理看板

**优先级**：P0（已完成）
**所属角色**：ADMIN
**对应 API**：`GET /api/admin/dashboard`, `GET /api/admin/export.csv`, `GET /api/admin/weekly_report.md`

**功能描述**：
展示近期安全运行数据总览，支持按天数（默认 30 天）和风险等级筛选，提供 CSV 和 Markdown 格式的数据导出。

**看板内容（6 个维度）**：

| 模块 | 内容 | 数据来源 |
|---|---|---|
| 核心指标 | 检查单数、通过率、培训通过率、待审核数 | CHECKLIST_RUNS_FILE + TRAINING_ATTEMPTS_FILE |
| 低置信 Top N | 知识不足最多的类别及数量 | LOW_CONFIDENCE_QUEUE_FILE |
| 近期高风险场景 | 最近 N 条高风险/阻断的开工检查记录 | CHECKLIST_RUNS_FILE |
| 事故摘要 | 按状态（open/review/action/verified/closed）统计 | INCIDENT_REVIEWS_FILE |
| 逾期事故 | 逾期未处理的事故列表（含逾期天数） | INCIDENT_REVIEWS_FILE + 日期计算 |
| 阻断原因分布 | Top 5 阻断原因（可选扩展） | CHECKLIST_RUNS_FILE |

**导出功能**：

| 导出类型 | 端点 | 说明 |
|---|---|---|
| CSV 导出 | `GET /api/admin/export.csv?scope=checklists\|training\|low_confidence\|incidents` | 4 种范围可选 |
| Markdown 周报 | `GET /api/admin/weekly_report.md` | 可附件发送 |

**筛选参数**：

| 参数 | 默认值 | 说明 |
|---|---|---|
| days | 30 | 统计天数范围，≤0 表示全部 |
| risk_level | "" | 风险等级过滤（空 = 全部） |
| incident_status | "" | 事故状态过滤（空 = 全部） |

**验收标准**：

| 标准 | 目标值 |
|---|---|
| 数据实时性 | 看板数据反映 CSV 文件最新状态 |
| CSV 导出完整性 | 4 种 scope 各返回完整字段 |
| 周报可读性 | Markdown 格式，可直接粘贴或附件发送 |

---

#### FR-06：应急卡片

**优先级**：P1（已完成）
**所属角色**：STUDENT, TEACHER
**对应 API**：`GET /api/emergency/cards`, `GET /api/emergency/match`, `POST /api/emergency/match`

**功能描述**：
用户用口语化描述输入事故场景，系统通过混合匹配找到最相关的应急卡片，展示处置步骤、禁止事项、PPE 要求和上报流程。

**已有卡片（12 张）**：

| ID | 标题 | 类别 |
|---|---|---|
| chemical_splash | Chemical Splash to Skin or Eyes | chemical |
| lab_fire | Small Laboratory Fire or Ignition | fire |
| electric_shock | Electrical Shock or Energized Equipment Incident | electrical |
| chemical_leak | Chemical Spill or Leak | spill |
| thermal_burn | Thermal Burn or Scald Injury | thermal |
| cut_injury | Cut, Puncture, or Bleeding Injury | mechanical |
| gas_leak | Gas Leak or Toxic Vapor Exposure | gas |
| cryogenic_exposure | Cryogenic Exposure or Cold Burn (Liquid Nitrogen / Dry Ice) | cryogenic |
| centrifuge_accident | Centrifuge Malfunction or Rotor Failure | mechanical |
| autoclave_accident | Autoclave or High-Pressure Equipment Incident | thermal |
| biological_exposure | Biological Exposure or Biohazard Spill | biosafety |
| ingestion_inhalation | Chemical Ingestion or Hazardous Inhalation | chemical |

**卡片内容结构**：

| 字段 | 说明 |
|---|---|
| title + category + summary | 标题、类别、一句话摘要 |
| trigger_signs | 触发征兆列表（"如果看到/闻到/感觉到…"） |
| immediate_actions | 立即处置步骤（有序列表） |
| forbidden | 禁止事项（红色高亮） |
| ppe | 所需 PPE |
| escalation | 升级上报流程（通知谁、打什么电话） |

**匹配方式**：bge-m3 语义检索 + 文本 token 匹配混合模式，语义权重 `EMERGENCY_SEMANTIC_WEIGHT=6.0`。

**验收标准**：

| 标准 | 目标值 |
|---|---|
| 全部 12 张卡片正确匹配 | 中文口语化查询命中正确卡片 |
| 匹配响应时间 | < 500ms |
| 卡片内容完整 | 每张含处置步骤、禁止事项、PPE、上报流程 |

**验证结果**（已通过）：

| 查询 | 命中卡片 |
|---|---|
| "眼睛被酸溅到了" | chemical_splash |
| "实验室着火了" | lab_fire |
| "有人触电了" | electric_shock |
| "化学品泄漏了" | chemical_leak |

---

#### FR-07：培训考核

**优先级**：P1（已完成）
**所属角色**：STUDENT, TEACHER, ADMIN
**对应 API**：`GET /api/training/questions`, `POST /api/training/submit`, `GET /api/training/stats`, `GET /api/training/roster_status`, `POST /api/training/roster_upload`, `GET /api/training/roster_template.csv`

**功能描述**：
从题库随机抽取题目生成考核会话，学生作答后自动评分并给出薄弱类别和推荐动作。老师/管理员可查看成绩统计和花名册完成情况。

**题库规格（50 题，10 个类别）**：

| 类别 | 题目数 | 覆盖内容 |
|---|---|---|
| PPE | 5 | 个人防护装备选择与使用 |
| Chemical | 5 | 化学品安全管理 |
| Electrical | 5 | 电气安全 |
| Waste | 5 | 废弃物处理 |
| Emergency | 5 | 应急处置 |
| Planning | 5 | 实验规划与准备 |
| Biosafety | 5 | 生物安全 |
| Incident | 5 | 事故报告与记录 |
| Mechanical | 5 | 机械设备安全 |
| Escalation | 5 | 上报流程与沟通 |
| **合计** | **50** | 单选 41 题 + 多选 9 题 |

**7.1 考核流程**：
1. 请求题目：`GET /api/training/questions?limit=5`（默认 5 题）
2. 返回 session_id + 题目列表（不含答案）
3. 学生作答后 POST 提交
4. 系统自动评分：逐题比对 selected_indices vs correct_indices
5. 返回成绩：score / total / passed / weak_categories / recommended_actions / 逐题回顾（含正确选项和解释）

**7.2 统计功能**：

| 统计项 | 说明 |
|---|---|
| attempt_count | 总尝试次数 |
| pass_rate | 通过率（默认 pass_threshold=80） |
| average_score | 平均分 |
| latest_submitted_at | 最近提交时间 |
| category_mistakes | 按类别统计错题分布 |
| recent_scores | 近期分数列表 |

**7.3 花名册功能**：

- **上传**：POST CSV 格式花名册（student_id, name, class_name, lab_group, required_training 五列）
- **状态查看**：total_required / completed_count / passed_count / incomplete_count / 未完成学生名单
- **模板下载**：`GET /api/training/roster_template.csv`

**验收标准**：

| 标准 | 目标值 |
|---|---|
| 题目随机性 | 每次请求不重复 |
| 评分准确性 | 逐题比对正确率 100% |
| 花名册导入 | CSV 正常解析，容错处理（无 student_id 时以 name 匹配） |
| 错题归档 | 每次提交的错题写入 training_mistakes.csv |

---

#### FR-08：事故复盘

**优先级**：P1（已完成）
**所属角色**：TEACHER, ADMIN
**对应 API**：`GET /api/incidents`, `POST /api/incidents`, `PATCH /api/incidents/{id}`, `DELETE /api/incidents/{id}`

**功能描述**：
记录和跟踪实验室安全事故/事件，支持全生命周期管理（CRUD），自动计算逾期状态和复发风险。

**事故状态流转**：

```
open (初始)
  → in_review (审查中)
    → action_in_progress (整改中)
      → verified (已验证)
        → closed (关闭)
```

**事故记录字段**：

| 字段 | 说明 |
|---|---|
| incident_id | 唯一 ID（格式 INC-YYYYMMDD-XXXXXXXX） |
| title + scenario | 事故标题 + 详细场景描述 |
| severity | low / medium / high / critical |
| status | open / in_review / action_in_progress / verified / closed |
| location | 发生地点 |
| cause_categories | 原因分类列表 |
| immediate_actions | 立即处置措施 |
| corrective_actions | 纠正措施 |
| owner | 负责人 |
| due_date | 整改截止日期 |
| closure_notes | 关闭备注 |
| recurrence_risk | 复发风险等级（自动计算：low/medium/high） |
| overdue | 是否逾期（自动计算） |
| overdue_days | 逾期天数（自动计算） |

**验收标准**：

| 标准 | 目标值 |
|---|---|
| CRUD 完整性 | 创建、查询（按状态/逾期筛选）、更新（状态流转）、删除全部正常 |
| 逾期自动计算 | due_date < today 且 status ≠ closed → overdue=true |
| 复发风险计算 | 基于严重性和历史同类事故频率自动评估 |

---

#### FR-09：低置信问题队列

**优先级**：P0（已完成，与 FR-01 联动）
**所属角色**：ADMIN
**关联 API**：融入 `POST /api/chat` 流程 + `GET /api/admin/dashboard`

**功能描述**：
当知识库检索 top score < 阈值（默认 3.5）时，系统不硬答，将问题自动写入低置信队列。管理员在看板中查看按频率排序的知识盲区列表，有针对性地补充知识库条目。

**队列字段**（17 个字段）：

| 字段 | 说明 |
|---|---|
| created_at | 入队时间 |
| question_hash | 问题去重哈希 |
| question | 原始问题文本 |
| mode | 问答模式 |
| decision | 决策标签 |
| risk_level | 风险等级 |
| matched_rule_id | 匹配到的规则 ID |
| matched_rule_action | 规则动作 |
| low_confidence_reason | 低置信原因 |
| citation_count | 引用数量 |
| top_score / top_kb_id / top_source_title | Top 检索结果信息 |
| suggested_lane | 建议处理通道 |
| suggested_action | 建议动作 |
| status | open / in_review / resolved |
| notes | 备注 |

**队列查看**：管理看板 `low_confidence_top` 字段返回按频率排序的盲区类别。

**正向循环机制**：

```
用户提问 → 检索失败 → 自动入队 → 管理员识别盲区
    → 定向补充知识库条目 → 检索能力提升 → 用户体验改善
```

**验收标准**：

| 标准 | 目标值 |
|---|---|
| 低置信自动入队 | top_score < 3.5 时 100% 写入队列 |
| 不硬答 | low_confidence=true 时返回保守提示 + "建议联系老师" |
| 队列可查看 | 管理员看板可看到按频率排序的盲区列表 |
| 队列可导出 | 支持 CSV 导出 |

---

### 4.3 功能需求矩阵

| 编号 | 功能 | 优先级 | 角色 | 核心 API | 状态 |
|---|---|---|---|---|---|
| FR-01 | 安全问答 | P0 | ALL | `POST /api/chat`, `GET /api/search` | ✅ 已完成 |
| FR-02 | 风险评估 | P0 | STUDENT | `POST /api/risk/assess` | ✅ 已完成 |
| FR-03 | 开工检查清单 | P0 | STUDENT | `POST /api/checklist/template`, `POST /api/checklist/submit` | ✅ 已完成 |
| FR-04 | 老师审核 | P0 | TEACHER | `PATCH /api/checklist/{id}/review` | ✅ 已完成 |
| FR-05 | 管理看板 | P0 | ADMIN | `GET /api/admin/dashboard` | ✅ 已完成 |
| FR-06 | 应急卡片 | P1 | STUDENT, TEACHER | `GET /api/emergency/match` | ✅ 已完成 |
| FR-07 | 培训考核 | P1 | ALL | `GET /api/training/questions`, `POST /api/training/submit` | ✅ 已完成 |
| FR-08 | 事故复盘 | P1 | TEACHER, ADMIN | `GET /api/incidents` | ✅ 已完成 |
| FR-09 | 低置信队列 | P0 | ADMIN | 融入 chat + dashboard | ✅ 已完成 |

---

## 5. 拟解决的关键问题

### 问题一：如何确保 AI 系统的安全边界不依赖 prompt？

**问题描述**：现有 AI 安全问答的安全边界依赖 prompt 指令（如"请不要回答危险问题"），但 prompt 可被绕过，且修改 prompt 需技术背景。

**本项目的解决方案**：
- 采用独立的 YAML 规则引擎，在 LLM 调用前进行确定性模式匹配
- 24 条规则覆盖 8 种 refuse 动作（高危模式如"金属钠+水""易燃溶剂+明火加热"）和 13 种 redirect_emergency 动作（事故场景如"着火""泄漏""触电"）
- 当匹配到危险模式时，规则引擎直接触发 refuse（拒绝回答）或 redirect_emergency（重定向应急卡片），**无需经过大模型判断**
- YAML 规则文件可由非技术人员修改，改完即生效，无需重新训练或调参

### 问题二：如何从"给一段文字"升级为"给一个判断"？

**问题描述**：普通 AI 问答返回一段 Markdown 文本，用户看完还需自行判断"到底能不能做"，且无法进行量化管理。

**本项目的解决方案**：
- API 返回结构化决策对象：`allow_start` / `blocking_reasons` / `review_status` / `next_actions` / `risk_level`
- 前端据此渲染三色决策卡片：绿（可开工）、黄（需确认）、红（暂不可开工）
- 管理看板可直接统计阻断率和阻断原因分布
- 将安全决策从模糊的文字描述转变为可量化、可追踪的结构化数据

### 问题三：知识库覆盖不全时如何持续演进？

**问题描述**：静态知识库总有盲区，如果系统在知识盲区强行生成答案，可能给出错误甚至危险的指导。

**本项目的解决方案**：
- 当知识库检索无法覆盖用户问题时，系统不强行生成不可靠的回答
- 将其标记为低置信问题（`low_confidence=true`），自动写入低置信队列
- 管理员可在看板中查看按类别和频率排序的知识盲区列表
- 有针对性地补充知识库条目，形成"使用 → 发现盲区 → 补充知识 → 更准确"的正向循环
- 这一机制将知识库从静态资源转变为可自我进化的知识资产

### 问题四：如何在不增加老师负担的前提下实现有效的人机协同？

**问题描述**：高风险实验的最终开工许可必须由老师确认（AI 不承担最终安全许可），但传统的逐一人工检查效率低、覆盖不全。

**本项目的解决方案**：
- AI 完成风险识别、摘要生成和缺失标记等预处理工作
- 老师仅需面对已经结构化的信息做最终判断
- 审核一个实验不超过 30 秒
- 系统完整记录决策证据链（学生自查时间、缺失项、系统建议、老师操作、时间戳）
- 既保护学生也保护老师

---

## 6. 非功能需求

### 6.1 性能

| 指标 | 目标值 | 备注 |
|---|---|---|
| 知识库文本检索响应时间 | < 500ms | 纯 token 匹配模式 |
| 知识库混合检索响应时间 | < 3s | 含 bge-m3 语义检索（首次构建索引 +10~30s） |
| API 端到端响应时间（P95） | < 5s | 含 LLM 调用 |
| 前端首屏加载 | < 2s | Vite 构建产物，gzip 后约 30KB JS + 10KB CSS |
| 并发用户数（MVP） | ≥ 10 | 单机 uvicorn，无数据库连接池瓶颈 |

### 6.2 可靠性

| 指标 | 目标值 | 策略 |
|---|---|---|
| 语义检索降级 | 100% 不崩溃 | Ollama 不可用时自动 fallback 到纯文本检索 |
| LLM 调用降级 | 100% 有兜底 | 调用失败后使用 `build_fallback_lab_answer` 结构化答案 |
| CSV 写入 | 即写即刷盘 | 每次写入直接落盘，不依赖内存缓存 |
| 启动时间 | < 5s | 不含首次 embedding 索引构建 |

### 6.3 安全性

| 要求 | 说明 |
|---|---|
| 不输出危险操作指导 | 24 条规则硬阻断（8 refuse + 13 redirect_emergency + 低置信兜底） |
| AI 不承担安全许可 | 所有输出为"建议""提示"，最终许可由老师确认 |
| 密钥不落地 | DIFY_APP_API_KEY / OPENAI_API_KEY 通过环境变量注入，`.env` 在 `.gitignore` 中 |
| 输入校验 | 全部 API 输入经 Pydantic 严格校验，长度限制防止滥用 |
| 系统字体栈 | 移除 Google Fonts 外部依赖，使用系统字体，避免网络阻断 |

### 6.4 可维护性

| 要求 | 说明 |
|---|---|
| 代码分层 | FastAPI router → service → repository 三层分离，单文件 ≤ 500 行 |
| 业务域拆分 | 10 个 service 文件，按业务域独立，互不交叉引用 |
| 测试覆盖 | 157 项 pytest（含 API 端点、服务逻辑、数据完整性、边界条件） |
| 规则可维护 | YAML 格式，非技术人员可直接修改，改完即生效 |
| 数据可迁移 | CSV/JSON 格式，可用 Excel / 文本编辑器直接打开编辑 |
| Docker 化 | Dockerfile 多阶段构建 + docker-compose.yml，一条命令启动 |

### 6.5 可观测性

| 要求 | 端点 | 说明 |
|---|---|---|
| 健康检查 | `GET /health` | 返回 `{"status": "ok"}` |
| 工作区状态 | `GET /api/workspace/status` | Dify 连接状态、知识库条数、低置信队列数、类别/危险分布 |
| 元信息 | `GET /api/meta` | 版本号、评测得分、稳定性状态、知识库行数 |
| API 文档 | `GET /docs` | FastAPI 自动生成的 Swagger UI |
| 日志 | uvicorn 输出 | stdout + `logs/` 目录文件日志（Docker volume 持久化） |

### 6.6 兼容性

| 维度 | 支持范围 |
|---|---|
| Python 版本 | 3.12 / 3.13 |
| 操作系统 | Windows 11（开发）/ Linux（Docker 生产） |
| 浏览器 | Chrome / Firefox / Edge 最新两个主版本 |
| Docker 架构 | amd64 / arm64（GitHub Actions 多架构构建） |
| Embedding 后端 | Ollama bge-m3 / sentence-transformers（备选） |

---

## 7. 数据需求

### 7.1 核心数据资产

| 数据 | 文件路径 | 格式 | 规模 | 说明 |
|---|---|---|---|---|
| 知识库 | `knowledge_base_curated.csv` | CSV | 142 条原始记录（含 bge-m3 向量索引后为 1148 条语义条目） | 16 字段：id, title, question, source_title, source_org, source_url, risk_level, category, subcategory, hazard_types, answer, steps, forbidden, emergency, ppe, tags |
| 安全规则 | `safety_rules.yaml` | YAML | 24 条（4 critical, 16 high, 3 medium, 1 low） | 每规则含 id, severity, patterns, action, response |
| 应急卡片 | `web_demo/data/emergency_cards.json` | JSON | 12 张 | 覆盖 10 种事故类型 |
| 培训题库 | `web_demo/data/training_question_bank.json` | JSON | 50 题 | 10 个类别，41 单选 + 9 多选 |
| 花名册模板 | `data_sources/training_roster_template.csv` | CSV | 模板文件 | 5 列：student_id, name, class_name, lab_group, required_training |

### 7.2 运行时数据

| 数据 | 文件路径 | 格式 | 写入频率 |
|---|---|---|---|
| 检查清单运行记录 | `artifacts/checklists/checklist_runs.csv` | CSV（16 字段） | 每次提交追加 |
| 培训尝试记录 | `artifacts/training/training_attempts.csv` | CSV（9 字段） | 每次提交追加 |
| 培训错题记录 | `artifacts/training/training_mistakes.csv` | CSV（10 字段） | 每次提交追加 |
| 事故记录 | `artifacts/incidents/incident_reviews.csv` | CSV（15+ 字段） | CRUD 全量覆写 |
| 低置信队列 | `artifacts/low_confidence_followups/data_gap_queue.csv` | CSV（17 字段） | 检测到低置信时追加 |
| Embedding 索引 | `.cache/embedding/` | Pickle | 首次构建后持久化，后续启动加载 |

### 7.3 知识库质量要求

| 指标 | 目标值 |
|---|---|
| 字段完整率 | ≥ 95% |
| 来源可追溯率 | ≥ 90% |
| 风险等级标注率 | 100% |
| 覆盖安全类别 | ≥ 6 大类（化学、生物、电气、机械、低温、综合） |

### 7.4 Embedding 索引缓存

- 知识库索引：`.cache/embedding/`（1148 条向量条目）
- 应急卡片索引：`.cache/embedding_emergency/`（12 条向量条目）
- 首次构建耗时：10~30 秒（取决于 Ollama 响应速度）
- 后续启动：秒级加载（pickle 反序列化）

---

## 8. 用户场景与验收用例

### 场景 1：学生高风险实验自查被阻断（核心演示场景）

```
前置条件：知识库已加载，Ollama 运行中

步骤 1：学生打开"实验场景输入"页面
  输入：
    - 实验名称：锂电池拆解
    - 试剂：N/A
    - 设备：金属工具、万用表
    - 步骤：用螺丝刀撬开外壳，取出电芯
    - 是否阅读 SOP：否
    - 是否查看 SDS：否
    - PPE：未穿戴绝缘手套
  点击"开始检查"

步骤 2：系统返回风险评估
  风险等级：High（4）或 Critical（5）
  危险类型：Electrical, Fire
  推荐 PPE：Electrical gloves, Face shield, Lab coat

步骤 3：系统生成个性化检查清单
  基础 6 项 + Electrical 专项（接地/绝缘确认）+ Fire 专项（点火源控制）+ 高风险追加 2 项
  = 共 10 项，其中 9 项为 Critical

步骤 4：学生故意不勾选 sop_reviewed、ppe_ready、high_risk_authorized
  提交 → allow_start=false
  blocking_reasons：
    - SOP, SDS, and experiment objective have been reviewed.
    - Required PPE is available, correctly worn, and suitable for this task.
    - Supervisor approval or buddy check is completed for this high-risk operation.
  review_status：pending

步骤 5：老师工作台出现一条待审核记录
  显示：学生姓名、实验场景、风险等级、阻断原因

预期结果：
  ✅ 学生看到红色决策卡 + 明确的阻断原因（不是模糊的"请注意安全"）
  ✅ 老师工作台自动收到待审核记录
  ✅ 管理看板统计数据更新
```

### 场景 2：低风险实验自动通过

```
步骤 1：学生输入场景："使用 pH 试纸测试自来水酸碱度，已阅读 SOP，穿实验服和护目镜"
步骤 2：系统返回风险等级：Low（1）或 Medium-Low（2）
步骤 3：生成基础 6 项检查清单 + scope_defined 补充项
步骤 4：学生勾选全部关键项 → 提交
步骤 5：allow_start=true, review_status=approved（自动通过，无需老师审核）

预期结果：
  ✅ 学生看到绿色决策卡
  ✅ 老师工作台不增加待审核项
  ✅ 记录已归档
```

### 场景 3：老师审核高风险实验

```
前置条件：存在一条 review_status=pending 的检查清单记录

步骤 1：老师打开工作台
步骤 2：查看看板，待审核数量 ≥ 1
步骤 3：展开某条待审核记录详情：
  - 学生：张三
  - 场景：锂电池拆解
  - 风险等级：High
  - 缺失项清单（3 条）
  - 系统建议："暂不可开工，请完成高亮项后联系老师确认"
步骤 4：老师输入评语："请先确认电池已完全放电，使用绝缘工具操作"
步骤 5：点击"驳回"

预期结果：
  ✅ 记录 review_status 变为 rejected
  ✅ review_comment 存储评语
  ✅ reviewed_at 记录时间戳
```

### 场景 4：应急卡片匹配

```
步骤 1：用户输入"眼睛被酸溅到了怎么办"
步骤 2：系统匹配到 chemical_splash 卡片
步骤 3：显示：
  - 标题：Chemical Splash to Skin or Eyes
  - 立即处置：用洗眼器或流动清水冲洗至少 15 分钟
  - 禁止事项：不要揉眼睛，不要使用中和剂
  - PPE：Chemical resistant gloves, Splash goggles
  - 上报：通知导师，拨打校医院电话

预期结果：
  ✅ 12 张卡片均能通过口语化中文查询正确匹配
  ✅ 紧急信息突出展示（红/橙高亮禁止事项）
```

### 场景 5：低置信兜底

```
步骤 1：用户提问："纳米材料合成需要注意什么安全问题？"
步骤 2：系统检索知识库，top_score 低于 3.5
步骤 3：返回回答：
  - low_confidence=true
  - 回答包含："建议联系实验室老师确认具体安全要求"
  - 问题写入低置信队列
步骤 4：管理员查看看板，低置信队列 Top N 中出现"纳米材料"类别

预期结果：
  ✅ 不确定时不硬答
  ✅ 问题自动入队
  ✅ 管理员可看到待补充的知识盲区
```

---

## 9. 实施计划

项目总周期：**2026 年 6 月 — 2028 年 6 月（共 2 年）**，分六个阶段实施。

### 第一阶段：需求校准与规则验证（2026.6 — 2026.8，3 个月）

| 任务 | 内容 | 交付物 |
|---|---|---|
| 任务 1 | 与指导教师深入沟通，选取 5+ 真实实验场景作为验证基准（有机合成/无机反应/生物实验/机械操作等） | 验证场景清单 |
| 任务 2 | 手工走查全部 24 条 YAML 规则，逐条验证触发条件、匹配模式和阻断动作 | 规则验证报告（含阻断准确率基线 ≥ 80%） |
| 任务 3 | 测试知识库检索召回率和准确率，分析检索失败原因 | 检索质量报告 |
| 任务 4 | 补充缺失的 YAML 规则（从 24 → 35+）和知识库条目（新增 30+） | 补充后的规则 + 知识库条目清单 |
| 任务 5 | 搭建 Vite 5 + TypeScript + Tailwind CSS 前端项目骨架 | 路由就绪、布局可用（`yarn dev` 通过） |
| 任务 6 | 编写前端 API 客户端层，封装 22 个 API 端点的类型安全请求函数 | `api/client.ts` + 完整 TypeScript 类型 |

### 第二阶段：前端页面开发与前后端联调（2026.9 — 2027.1，5 个月）

分三批完成 8 个页面，每批"开发一页、联调一页、验收一页"：

**第一批（2026.9 — 2026.10）核心用户流程**：

| 页面 | 核心组件 |
|---|---|
| 实验场景输入 | 实验名称输入框、试剂标签动态添加、设备多选下拉、操作步骤文本域、表单验证 |
| 风险决策结果 | 三色决策卡片组件（红/黄/绿）、风险等级与评分、危险类型标签、阻断原因逐条展示、引用来源面板 |
| 检查清单交互 | 动态表单渲染（critical 项红色边框高亮）、逐项勾选+备注、提交前完整性校验 |

**第二批（2026.11）辅助功能**：

| 页面 | 核心组件 |
|---|---|
| 安全问答 | 对话气泡（Markdown 渲染）、SSE 流式响应、引用来源内嵌、低置信提示横幅 |
| 应急卡片 | 12 张卡片网格布局、类别筛选按钮、口语化搜索框实时匹配、详情弹窗 |
| 培训考核 | 类别选择面板、单选/多选渲染、即时出分+错题回顾、历史成绩列表 |

**第三批（2026.12 — 2027.1）管理与闭环**：

| 页面 | 核心组件 |
|---|---|
| 老师审核工作台 | 审批队列列表、实验详情展开面板、批准/驳回操作区（常用评语模板） |
| 管理看板 | 统计卡片行、阻断原因分布、培训通过率趋势、知识盲区列表、CSV 导出按钮 |

### 第三阶段：试点部署与反馈收集（2027.2 — 2027.6，5 个月）

| 任务 | 内容 |
|---|---|
| 部署 | 在指导教师实验室/课程环境中 Docker 部署，配置 Nginx 反向代理 |
| 试点 | 选取 1-2 门课程约 50-100 名学生进行真实试点 |
| 数据收集 | 收集阻断率、低置信分布、检索召回率、审核通过率等真实运行数据 |
| 用户调研 | 访谈 10+ 名学生和 2+ 名老师，收集改进意见 |
| 迭代优化 | 根据反馈调整规则阈值、补充知识库、优化前端交互 |

### 第四阶段：知识库扩展与评测体系（2027.7 — 2027.12，6 个月）

| 任务 | 内容 |
|---|---|
| 知识库扩展 | 定向补充试点发现的知识盲区，新增 50+ 条 |
| 规则扩展 | 根据试点反馈新增 10+ 条 YAML 规则 |
| 评测集建设 | 建立 50+ 题的标准化评测集 |
| 自动化评测 | 实现一键回归测试 + 评分报告生成 |
| 文档完善 | 编写用户手册、部署手册、维护手册 |

### 第五阶段：系统完善与多场景适配（2028.1 — 2028.3，3 个月）

| 任务 | 内容 |
|---|---|
| 系统稳定性 | 长稳测试、异常降级验证、Docker 健康检查验证 |
| 数据存储升级 | CSV → SQLite 迁移（支持并发写入） |
| 多课程支持 | 支持按课程/实验室隔离数据和看板 |
| 本地 LLM 接入 | 支持 Ollama 本地模型（如 Qwen）作为 LLM 后端 |

### 第六阶段：结题收口与成果整理（2028.4 — 2028.6，3 个月）

| 任务 | 内容 |
|---|---|
| 结题报告 | 撰写结题报告，整理需求/设计/实现/测试/部署全链文档 |
| 论文/软著 | 投递 1-2 篇相关论文，申请软件著作权 |
| 成果展示 | 制作演示视频、项目海报、成果展板 |
| 开源发布 | 清理仓库，撰写 README，准备 GitHub 公开发布 |
| 答辩准备 | 整理答辩 PPT 和现场演示脚本 |

---

## 10. 预期成果

| 类别 | 预期成果 | 数量/目标 |
|---|---|---|
| 软件系统 | Lab Safety Copilot 完整 Web 应用 | 1 套 |
| 知识库 | 结构化实验室安全知识条目 | 142+ 条（含向量索引 1148+ 条） |
| 安全规则 | YAML 安全规则 | 24+ 条 |
| 应急卡片 | 实验室事故应急处理卡片 | 12 张 |
| 培训题库 | 安全培训考核试题 | 50 题（10 类别） |
| 源代码 | 完整后端 + 前端源代码 | 约 50+ 文件，10000+ 行 |
| 测试 | pytest 自动化测试 | 157+ 项 |
| 论文 | 发表相关学术论文 | 1-2 篇 |
| 软著 | 软件著作权登记 | 1 项 |
| 用户手册 | 系统使用与部署手册 | 1 份 |
| 评测报告 | 系统性能与准确率评测报告 | 1 份 |
| 试点报告 | 真实用户试点反馈报告 | 1 份 |

---

## 11. 版本历史

| 版本 | 日期 | 变更说明 |
|---|---|---|
| v1.0 | 2026-03 | v8.2 演示基线版本，基于 Dify 工作流 |
| v1.5-draft | 2026-04-28 | 申报书兑现版需求规格初稿 |
| v2.0 | 2026-04-29 | no-Dify 重定位版完整需求规格，对齐申报书数据 |
