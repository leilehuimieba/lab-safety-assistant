# Status

## 当前状态
- active

## 当前步骤
- 已暂停申报书兑现主线。
- 已建立 no-Dify 新需求主线。
- 已产出 PRD 和 change 五件套。
- 已完成重构前端导入（Vite SPA + 后端适配）。
- 下一步进入 no-Dify MVP 剩余功能实现与验证。

## 已完成
- 已确认用户新指令：不再管申报书，重新对接需求。
- 已确认新产品方向：`Lab Safety Copilot / 实验前安全检查助手`。
- 已确认 Dify 不再作为核心依赖，仅保留为历史 demo 或可选链路。
- 已新增 PRD：`docs/product/prd_lab_safety_copilot_no_dify_20260428.md`。
- 已新增 change：`docs/changes/2026-04-28-demand-realignment-no-dify/`。
- 已切换 active change。
- 已同步路线图、执行入口和待办。
- 已完成重构前端导入（Vite + TS + Tailwind SPA），源码位于 `web_demo/frontend/`。
- 已完成后端静态文件服务与 SPA 路由回退适配。
- 已完成 API 兼容层（别名路由、缺失路由、数据模型适配）。
- 已修复后端若干导入缺失导致的 500 错误（`within_days`、`TRAINING_ATTEMPTS_FILE`、`INCIDENT_REVIEWS_FILE`）。

## 未完成
- 尚未拆分第一轮代码实现任务。
- 尚未实现 no-Dify 实验前自查最小闭环。
- 尚未把 Dify 依赖从当前演示主链路中降级为可选链路。
- 尚未完成新的回归测试集。
- 新前端 HTTP 层验证已全部通过；浏览器自动化验证因 MCP 工具环境问题无法完成，需人工本地走查。

## 阻塞
- 当前无硬阻塞。

## 下一步
1. 按 PRD 拆分第一轮 MVP 实现任务。
2. 优先实现：实验前自查输入 -> 风险阻断 -> 老师审核包。
3. 再实现：本地知识库问答 -> 低置信队列 -> 管理看板。
4. 最后补 pytest 回归和浏览器走查。

## 最近更新时间
- 2026-04-28 21:50
