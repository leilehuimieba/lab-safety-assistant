# Design

## 目标概述
- 建立新的需求主线：项目不再围绕 Dify 平台接入和申报书指标展开，而是围绕“实验前安全检查助手 / Lab Safety Copilot”进行轻量自研 MVP。

## 方案概要
- 一句话方案：保留现有 FastAPI/web_demo/规则/知识库/评测资产，弱化 Dify 为可选历史链路，把核心功能切到本地规则 + 本地检索 + 模型直连 + 老师审核闭环。
- 主流程：
  1. 用户输入实验场景、试剂、设备、步骤、PPE、是否看过 SOP/SDS。
  2. 规则引擎先识别高风险和硬阻断项。
  3. 本地知识库检索相关 SOP/SDS/制度/应急卡片。
  4. 模型直连生成风险摘要、检查单和老师确认建议。
  5. 规则二次校验，输出 `允许 / 需老师确认 / 暂不可开工`。
  6. 高风险和低置信问题进入老师工作台 / 知识缺口队列。

## 关键决策
- 决策 1：Dify 不再作为核心依赖；可保留为历史 demo 或可选 backend。
- 决策 2：产品定位从“AI 安全问答系统”升级为“实验前安全检查助手”。
- 决策 3：MVP 只做学生自查、风险阻断、老师审核、安全问答、低置信队列、管理看板，不做完整 EHS。
- 决策 4：安全责任不交给 AI；AI 只做辅助自查、风险提示和老师确认建议。
- 决策 5：优先使用现有 FastAPI + 本地文件/SQLite + YAML 规则 + pytest，符合 vibe coding 快速实现。

## 影响模块
- 文档：`docs/product/prd_lab_safety_copilot_no_dify_20260428.md`
- 后续代码可能影响：
  - `web_demo/services/risk_service.py`
  - `web_demo/services/kb_service.py`
  - `web_demo/services/answer_service.py`
  - `web_demo/services/dashboard_service.py`
  - `web_demo/routers/*`
  - `safety_rules.yaml`
  - `knowledge_base_curated.csv`
- 当前不立即修改代码。

## 对展示主线的影响
- 对演示链路：后续演示主线应改成 `首页 -> 实验前自查 -> 阻断结论 -> 老师审核 -> 知识缺口/看板`。
- 对门禁 / 验证：后续 Gate 应验证高风险阻断、老师审核包、来源引用、低置信队列，而不是验证 Dify workflow。
- 对答辩材料：对外讲“补足现有 EHS 平台和 AI 问答在实验前即时决策上的空缺”。

## 风险与取舍
- 风险：放弃 Dify 作为核心链路后，需要自己维护检索、规则和模型调用。
- 取舍原因：自研链路更可控、更适合 vibe coding、更容易测试，也更贴合核心产品价值。

## 未决问题
- 模型直连选型：OpenAI-compatible、本地模型或两者都支持？
- 数据存储选型：MVP 继续 JSON/CSV，还是直接迁移 SQLite？
- 前端是否保留现有单页 HTML，还是改 Vite/React？
- 真实试点先选哪类实验场景：化学、电气、锂电池、机加工还是通用教学实验？

## 不做项
- 不做完整学校 EHS 平台。
- 不做全量库存 / 采购 / 门禁 / SSO。
- 不要求接入 Dify、MCP 或其他低代码平台。
- 不让 AI 直接给最终安全许可。
