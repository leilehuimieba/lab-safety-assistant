# Tasks

## 当前目标
- 暂停申报书主线，建立 no-Dify 的新需求主线，并产出可直接指导 vibe coding 的 PRD。

## 任务清单
- [x] T1: 明确用户指令：暂停申报书主线，重新对接需求
- [x] T2: 建立 `2026-04-28-demand-realignment-no-dify` change
- [x] T3: 暂停 `2026-04-28-application-requirements-fulfillment`
- [x] T4: 切换 active change
- [x] T5: 新建 no-Dify PRD
- [x] T6: 同步 `docs/README.md` 当前主线
- [x] T7: 同步 `docs/roadmap.md` 当前阶段
- [x] T8: 同步 `docs/reports/UNIFIED_TODO_BOARD.md` 新待办
- [x] T9: 导入重构前端（Vite SPA）到 `web_demo/frontend/`
- [x] T10: 后端 API 兼容层与静态文件服务适配
- [ ] T11: 下一步拆分 no-Dify MVP 实现任务
- [ ] T12: 下一步实现实验前自查 + 阻断 + 老师审核最小闭环

## P0 后续实现任务

| 编号 | 任务 | 完成判据 |
|---|---|---|
| NO-DIFY-MVP-01 | 实验前自查表单 | 用户可输入实验名称、试剂、设备、步骤、PPE、SOP/SDS 状态 |
| NO-DIFY-MVP-02 | 风险等级与阻断规则 | 高风险 / 缺关键项时输出 `暂不可开工` 或 `需老师确认` |
| NO-DIFY-MVP-03 | 检查清单生成 | 系统能生成可勾选的开工前检查清单 |
| NO-DIFY-MVP-04 | 老师审核包 | 高风险提交可生成老师摘要：风险、缺失项、建议动作 |
| NO-DIFY-MVP-05 | 安全问答本地检索 | 不依赖 Dify，能从本地知识库返回带来源答案 |
| NO-DIFY-MVP-06 | 低置信问题队列 | 知识库未命中或低置信问题进入待补知识队列 |
| NO-DIFY-MVP-07 | 管理看板 | 展示高风险场景、阻断原因、低置信问题、待审核数量 |
| NO-DIFY-MVP-08 | MVP 回归测试 | pytest 覆盖阻断、来源引用、低置信队列和老师审核包 |

## 依赖关系
- T10 依赖 T9 拆分完成。
- NO-DIFY-MVP-02 依赖 NO-DIFY-MVP-01。
- NO-DIFY-MVP-04 依赖 NO-DIFY-MVP-02。
- NO-DIFY-MVP-06 依赖 NO-DIFY-MVP-05。
- NO-DIFY-MVP-08 依赖 MVP 核心功能完成。

## 当前执行项
- 当前正在推进：需求重定位文档和项目主线切换。
- 下一步：基于 PRD 拆出第一轮代码实现任务。

## 阻塞项
- 当前无硬阻塞。
- 后续若要真实试点，需要确定 3-5 个典型实验场景和老师审核规则。

## 完成定义
- [x] proposal 已确认
- [x] design 已确认
- [x] PRD 已落地
- [x] active change 已切换
- [x] docs/README 已同步
- [x] roadmap 已同步
- [x] 统一待办已同步
- [ ] MVP 实现任务已拆分
- [ ] MVP 最小闭环已实现并验证
