# Tasks

## 当前目标
- 将项目主线收敛到 no-Dify 自研轻量版 `实验安全前置哨 / Lab Safety Copilot`。
- 清理 Dify / 申报书 / v8.2 旧主线文档口径，补齐当前定位、运行入口和 MVP 验收清单。
- 下一步重点从“继续扩功能”切换为“实现现状对齐 + 主链路验收 + 测试修复”。

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
- [x] T11: 补充当前 no-Dify 定位文档与 MVP 验收清单
- [x] T12: 删除/降级一批明确过时或被替代的旧文档
- [ ] T13: 建立 FR-01 到 FR-09 的实现对齐表
- [ ] T14: 按 no-Dify MVP 验收清单跑通主链路
- [ ] T15: 修复剩余 pytest 失败项并更新验证证据

## P0 验收任务

| 编号 | 任务 | 完成判据 |
|---|---|---|
| NO-DIFY-ALIGN-01 | FR-01 到 FR-09 实现对齐 | 文档列出每个功能对应 API、service、前端页面、测试文件和当前状态 |
| NO-DIFY-MVP-01 | 实验前自查表单 | 用户可输入实验名称、试剂、设备、步骤、PPE、SOP/SDS 状态 |
| NO-DIFY-MVP-02 | 风险等级与阻断规则 | 高风险 / 缺关键项时输出 `暂不可开工` 或 `需老师确认` |
| NO-DIFY-MVP-03 | 检查清单生成 | 系统能生成可勾选的开工前检查清单 |
| NO-DIFY-MVP-04 | 老师审核包 | 高风险提交可生成老师摘要：风险、缺失项、建议动作 |
| NO-DIFY-MVP-05 | 安全问答本地检索 | 不依赖 Dify，能从本地知识库返回带来源答案 |
| NO-DIFY-MVP-06 | 低置信问题队列 | 知识库未命中或低置信问题进入待补知识队列 |
| NO-DIFY-MVP-07 | 管理看板 | 展示高风险场景、阻断原因、低置信问题、待审核数量 |
| NO-DIFY-MVP-08 | MVP 回归测试 | pytest 覆盖阻断、来源引用、低置信队列和老师审核包 |
| NO-DIFY-DOC-01 | 文档口径清理 | README、docs/INDEX、active change、guides 均指向 no-Dify 当前主线；旧文档降级为历史/可选 |

## 依赖关系
- NO-DIFY-MVP-02 依赖 NO-DIFY-MVP-01。
- NO-DIFY-MVP-04 依赖 NO-DIFY-MVP-02。
- NO-DIFY-MVP-06 依赖 NO-DIFY-MVP-05。
- NO-DIFY-MVP-08 依赖 MVP 核心功能完成。
- NO-DIFY-ALIGN-01 应先于继续新功能开发。

## 当前执行项
- 当前正在推进：文档口径清理与当前定位补齐。
- 下一步：基于 `docs/ops/no_dify_mvp_acceptance_checklist.md` 验证主链路。

## 阻塞项
- 当前无硬阻塞。
- 历史文档数量较多，仍可能残留 Dify / v8.2 / 申报书旧口径；后续需要分批归档或标注历史状态。
- 后续若要真实试点，需要确定 3-5 个典型实验场景和老师审核规则。

## 完成定义
- [x] proposal 已确认
- [x] design 已确认
- [x] PRD 已落地
- [x] active change 已切换
- [x] docs/README 已同步
- [x] roadmap 已同步
- [x] 统一待办已同步
- [x] 当前定位摘要已补充
- [x] no-Dify MVP 验收清单已补充
- [x] 过时/被替代文档已第一批清理
- [ ] FR-01 到 FR-09 实现对齐表已补齐
- [ ] MVP 最小闭环已从 clean baseline 验证
- [ ] 自动化测试已全绿或失败项已有明确豁免说明
