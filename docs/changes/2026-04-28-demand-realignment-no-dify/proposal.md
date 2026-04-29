# Proposal

## change 名称
2026-04-28-demand-realignment-no-dify

## 日期
2026-04-28

## 当前状态
- active

## 背景 / 问题
- 用户明确要求暂停申报书主线，重新对接需求。
- 现有项目一度围绕申报书和 Dify/RAG 平台推进，但当前判断是：本项目属于 vibe coding 快速迭代，不适合把 Dify 平台作为核心依赖。
- Dify 能快速搭 demo，但会引入平台配置、workflow、知识库导入、MCP/接口编排等额外复杂度，反而增加完成难度。
- 重新调研后，当前更有价值的产品空缺不是“再做一个 EHS 大平台”或“Dify 问答机器人”，而是面向学生和老师的轻量级“实验前安全检查助手 / Lab Safety Copilot”。

## 服务阶段
- 新阶段：需求重定位与 no-Dify 自研 MVP 规划。
- 暂停：`2026-04-28-application-requirements-fulfillment` 申报书兑现主线。
- 保留：`v8.2` 演示基线作为历史原型和可复用能力，不作为新需求核心约束。

## 目标
- 将项目主线从“申报书 / Dify 平台 / 大而全 RAG”切换到“实验前安全检查助手 / 自研轻量 MVP”。
- 明确目标用户、竞品空缺、核心痛点和 MVP 功能。
- 明确不做范围：不把 Dify 作为必选依赖，不做完整 EHS 平台，不做全量危化品库存，不做正式 SSO。
- 产出新的 PRD 和技术路线，为后续 vibe coding 实现提供直接依据。

## 非目标
- 本次不继续推进申报书 `≥3000` 条知识库指标。
- 本次不继续把 Dify 作为唯一正式问答链路。
- 本次不做大范围业务代码重构。
- 本次不删除已有申报书文档和 v8.2 演示文档。
- 本次不承诺替代学校正式 EHS 平台。

## 范围
- 包含：
  - 新建 no-Dify 需求重定位 change 五件套
  - 新建 PRD：`docs/product/prd_lab_safety_copilot_no_dify_20260428.md`
  - 更新 `docs/changes/INDEX.md` 和 `docs/changes/active.txt`
  - 更新 `docs/README.md` 当前主线
  - 更新 `docs/roadmap.md` 当前阶段
  - 更新 `docs/reports/UNIFIED_TODO_BOARD.md` 新 P0 待办
- 不包含：
  - 立即移除 Dify 代码
  - 立即重写全部 web_demo
  - 立即实现登录、SSO、库存、门禁、IoT

## 影响面
- 影响模块：产品定位、需求文档、开发路线、待办优先级。
- 影响演示链路：保留现有演示能力，但后续主讲口径改为“实验前安全检查助手”。
- 影响发布 / 验证链路：后续评测从“Dify 问答是否通”转向“实验前自查、阻断、老师审核、低置信队列是否闭环”。

## 验收标准
- [x] 已建立 no-Dify 新需求 change。
- [x] 已暂停申报书兑现 change。
- [x] 已切换 active change。
- [x] 已新增 PRD。
- [x] 已同步 docs/README、roadmap、changes index 和统一待办。
- [ ] 后续完成 MVP 设计稿和任务拆分。
- [ ] 后续完成 no-Dify 自研 MVP 最小实现。

## 风险
- 需求重定位会改变原有申报书 / Dify 口径，后续答辩或结题若仍需申报书材料，需要单独恢复或引用已暂停文档。
- 弱化 Dify 后，需要确保本地知识库检索、规则和模型直连能力能支撑核心场景。
- 如果 scope 又扩成完整 EHS 平台，会失去 vibe coding 的速度优势。

## 回退方案
- 回退点：`docs/changes/2026-04-28-application-requirements-fulfillment/` 和 `v8.2` 演示基线仍保留。
- 回退条件：用户重新要求按申报书或 Dify 平台推进。
- 回退步骤：将 `docs/changes/active.txt` 改回对应 change，并恢复 `docs/README.md` / `docs/roadmap.md` 当前主线描述。
