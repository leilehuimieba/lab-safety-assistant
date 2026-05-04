# 项目执行入口

## 1. 项目概况
- 项目名称：实验室安全小助手
- 项目目标：面向高校实验室场景，提供可追溯、可控的安全问答、风险评估与应急引导能力
- 项目定位：课程 / 大创展示优先
- 当前演示基线版本：`v8.2`
- 当前次级目标：后续平台化与稳定化

## 2. 当前唯一执行主线
- 当前主线：暂停申报书与 Dify 平台导向，重新定位为 no-Dify 自研轻量版 `Lab Safety Copilot / 实验前安全检查助手`
- 当前优先事项：
  1. 明确新产品不再把 Dify 作为核心依赖
  2. 围绕“学生实验前自查 -> 风险阻断 -> 老师审核 -> 管理看板”建立 MVP
  3. 优先产出 no-Dify PRD、MVP 任务拆分和本地自研实现路线
  4. 保留现有 `v8.2` 能力作为可复用资产，但后续 Gate 不再围绕 Dify workflow
  5. 后续验证重点改为高风险阻断、老师审核包、来源引用、低置信队列和本地可运行
- 当前不优先事项：
  1. 非必要的大范围重构
  2. 以 prod 上线或完整 EHS 平台为前提的过度工程
  3. 与实验前安全检查 MVP 无关的扩展功能
  4. 继续把 Dify、MCP 或低代码平台配置作为主交付

## 3. 当前阶段入口
- 当前阶段：见 `docs/roadmap.md`
- 当前主推进 change：见 `docs/changes/INDEX.md`
- 若没有 active change：先建立 change，再推进中等以上任务

## 4. 默认执行顺序
1. 读 `AGENTS.md`
2. 读 `docs/README.md`
3. 读 `docs/roadmap.md`
4. 读 `docs/changes/INDEX.md`
5. 读 active change 的 `status.md`
6. 读 active change 的 `tasks.md`
7. 必要时再读 `design.md` / `verify.md`
8. 需要项目背景时再读根 `README.md`、`docs/reports/PROJECT_STATUS.md`、相关 `docs/eval/` / `docs/ops/`

## 5. 文档冲突优先级
1. 用户最新明确指令
2. 当前活跃 change 的 `status.md` / `tasks.md`
3. 当前活跃 change 的 `design.md`
4. `docs/roadmap.md`
5. 本文档
6. 最新日期的门禁、验收、go-live 证据文档
7. `docs/reports/PROJECT_STATUS.md`、`docs/PROJECT_STRUCTURE.md` 等说明文档
8. `docs/archive/` 历史只读文档

## 6. 当前版本口径
- 当前演示基线：`v8.2`
- 当前产品新定位：`Lab Safety Copilot / 实验前安全检查助手`
- 当前展示主 Gate：no-Dify MVP 可本地运行 + 实验前自查 / 阻断 / 老师审核 / 看板闭环可演示
- 当前暂停项：申报书 `1000 -> 3000` 知识库扩容和 Dify workflow 主链路
- 当前平台化次级 Gate：prod / go-live readiness，暂不作为首要推进目标

## 7. 当前主线判断依据
- no-Dify 新 PRD：`docs/product/prd_lab_safety_copilot_no_dify_20260428.md`
- 当前主推进 change：`docs/changes/2026-04-28-demand-realignment-no-dify/`
- 申报书兑现主线已暂停：`docs/changes/2026-04-28-application-requirements-fulfillment/`
- 最新发布包：`release_exports/v8.2/`
- `v8.2` 作为历史原型和可复用资产，不作为后续需求边界的唯一来源

## 7A. 本地运行与可选历史链路
- 默认工作区：`D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github`
- 默认本地 web_demo 入口：`http://127.0.0.1:8088`
- 当前主链路：no-Dify 本地 FastAPI + 规则引擎 + 本地知识库 + 可选模型直连
- Dify 相关入口、token 和 bridge 脚本只作为历史 v8.2 演示或可选兼容链路，不作为当前 MVP Gate
- 当前验收入口：`docs/ops/no_dify_mvp_acceptance_checklist.md`

## 7B. 本地 / 服务器目录与同步口径
- 当前唯一默认事实源：`D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github`
- 当前推荐服务器唯一正式部署目录：`/root/lab-safe-assistant-github`
- `local_env/`、`artifacts/`、`logs/`、`output/`、`.venv*`、`_tmp_*` 不属于服务器标准同步内容
- 具体同步规范见：`docs/ops/local_server_sync_plan_cn.md`
- 最后一轮人工计时彩排与 Gate 盖章执行包见：`docs/ops/v8_2_demo_timed_rehearsal_execution_pack_cn.md`

## 8. 缺口处理规则
如果缺少：
- 当前阶段
- 当前 active change
- `tasks.md`
- `status.md`
- `verify.md`

则先输出缺口，不直接进入编码。
