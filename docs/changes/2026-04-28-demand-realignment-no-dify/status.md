# Status

## 当前状态
- active

## 当前阶段
- Phase 5 - no-Dify 需求重定位与轻量 MVP

## 当前步骤
- 已暂停申报书兑现主线。
- 已建立 no-Dify 新需求主线。
- 已产出 PRD、正式需求规格、系统设计和 change 五件套。
- 已完成重构前端导入（Vite SPA + 后端适配）。
- 已完成后端静态文件服务与 SPA 路由回退适配。
- 已补充当前定位摘要与 no-Dify MVP 验收清单。
- 下一步应进入“实现现状对齐 + MVP 主链路验收 + 测试修复”，而不是继续扩大功能范围。

## 已完成
- 已确认用户新指令：不再以申报书 / Dify 平台作为当前主线，重新对接需求。
- 已确认新产品方向：`实验安全前置哨 / Lab Safety Copilot / 实验前安全检查助手`。
- 已确认 Dify 不再作为核心依赖，仅保留为历史 demo 或可选兼容链路。
- 已新增 PRD：`docs/product/prd_lab_safety_copilot_no_dify_20260428.md`。
- 已新增正式需求规格：`docs/product/requirements_spec_20260429.md`。
- 已新增系统设计文档：`docs/product/design_spec_20260429.md`。
- 已新增当前定位摘要：`docs/product/current_positioning_20260501.md`。
- 已新增 no-Dify MVP 验收清单：`docs/ops/no_dify_mvp_acceptance_checklist.md`。
- 已新增 change：`docs/changes/2026-04-28-demand-realignment-no-dify/`。
- 已切换 active change。
- 已同步路线图、执行入口和待办。
- 已完成重构前端导入（Vite + TS + Tailwind SPA），源码位于 `web_demo/frontend/`。
- 已完成后端静态文件服务与 SPA 路由回退适配。
- 已完成 API 兼容层（别名路由、缺失路由、数据模型适配）。
- 已修复后端若干导入缺失导致的 500 错误（`within_days`、`TRAINING_ATTEMPTS_FILE`、`INCIDENT_REVIEWS_FILE`）。
- 已将旧 Dify starter / 规则说明改写为 no-Dify 本地规则引擎口径。
- 已删除被新文档替代的旧命名需求/设计文档和若干暂停主线草稿。

## 未完成
- 尚未完成 FR-01 到 FR-09 的“代码入口 / API / 前端页面 / 测试覆盖”逐项对齐表。
- 尚未从 clean baseline 完整跑通 no-Dify MVP 主链路验收清单。
- 尚未把所有文档中的 v8.2 / Dify 旧口径完全降级为历史或可选口径。
- 尚未修复交接口径中提到的 2 个 `test_eval_smoke.py` 失败项。
- 浏览器自动化验证此前受 MCP 工具环境问题影响，仍需人工本地走查或换工具验证。

## 当前阻塞
- 当前无硬阻塞。
- 软阻塞：历史文档很多，仍包含 Dify / v8.2 / 申报书旧口径；后续应继续分批归档或降级，避免和当前主线混淆。

## 下一步
1. 按 `docs/ops/no_dify_mvp_acceptance_checklist.md` 跑一轮 API + 浏览器主链路验收。
2. 建立 FR-01 到 FR-09 的实现对齐表，标明对应 API、服务、前端页面和测试文件。
3. 修复 `test_eval_smoke.py` 中剩余失败项，使 `python -m pytest -q` 全绿。
4. 将当前文档清理结果提交，避免新旧需求文档混杂。
5. 如后续仍要保留 Dify / v8.2 文档，统一加“历史 / 可选链路”说明，不再作为当前 Gate。

## 最近更新时间
- 2026-05-01
