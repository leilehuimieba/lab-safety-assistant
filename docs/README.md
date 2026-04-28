# 项目执行入口

## 1. 项目概况
- 项目名称：实验室安全小助手
- 项目目标：面向高校实验室场景，提供可追溯、可控的安全问答、风险评估与应急引导能力
- 项目定位：课程 / 大创展示优先
- 当前演示基线版本：`v8.2`
- 当前次级目标：后续平台化与稳定化

## 2. 当前唯一执行主线
- 当前主线：围绕 `v8.2` 演示链路收敛文档、验证、脚本与答辩可复现性
- 当前优先事项：
  1. 保证演示链路可复现
  2. 保证关键场景有验证证据
  3. 保证答辩材料与项目口径一致
- 当前不优先事项：
  1. 非必要的大范围重构
  2. 以 prod 上线为前提的过度工程
  3. 与展示主线无关的扩展功能

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
- 当前展示主 Gate：demo 可复现 + 关键验证通过
- 当前平台化次级 Gate：prod / go-live readiness，暂不作为首要推进目标

## 7. 当前主线判断依据
- 最新发布包：`release_exports/v8.2/`
- `docs/eval/v8_2_release_summary.md` 明确说明：`v8.2` 数据扩容和 20 题 demo 回归可继续用于线上演示
- `docs/ops/go_live_readiness.md` 显示 prod / readiness 仍有阻塞，因此当前不以正式上线为第一优先级

## 7A. 新路径默认展示口径（本地 Dify）
- 默认工作区：`D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github`
- 默认本地 Dify 入口：`http://127.0.0.1:8081`
- 默认本地 web_demo 入口：`http://127.0.0.1:8088`
- 默认展示 app token：`app-wRwHKLfNDGRk4jfCfYeifipT`
- 默认展示 app 类型：`advanced-chat（实验室安全小助手）`
- 当前展示链路口径：
  - lab lane：`Dify 正式知识库工作流`
  - agent lane：`OpenAI 兼容直连`

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
