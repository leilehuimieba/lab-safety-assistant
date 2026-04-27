# Verify

## 验证范围
- 覆盖什么：新工作区复制、Dify 配置迁入、Docker Desktop 恢复、新路径下 Dify 入口与现有 setup/app/token 状态验证、`web_demo` 接回本地 Dify 的接口级验证、浏览器级展示回归、浏览器截图证据补齐、旧路径默认入口口径清理、历史报告口径标注收尾。
- 不覆盖什么：历史绝对路径全量替换、服务器链路验证。

## 验证方法
- 命令：
  - `docker version`
  - `docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"`
  - `docker compose -f D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github\local_env\dify\docker\docker-compose.yaml ps`
  - 访问 `http://127.0.0.1:8080/console/api/setup`
  - 访问 `http://127.0.0.1:8088/api/meta`
  - `POST http://127.0.0.1:8088/api/chat` with `mode=lab`
  - `POST http://127.0.0.1:8088/api/chat` with `mode=agent`
  - `rg -n --hidden ... "D:\\workspace\\lab-safe-assistant-github|D:\\workspace\\data|D:\\workspace" D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github`
- 手工步骤：
  - 浏览器打开 `http://127.0.0.1:8088`
  - 侧边栏切换到“平台总览 / 智能问答 / 本地 Dify / 准入阻断”
  - 在“智能问答”页分别验证 `lab` 与 `agent` 问答
  - 对关键视图执行截图留档
  - 逐个检查当前操作脚本与当前操作文档中的 `D:\workspace` 是否仍作为默认执行入口出现
  - 对剩余历史报告逐个检查，确认已补“历史路径说明”而不是直接改写历史路径字段
- 场景：Windows 本机新工作区 `D:\newwork`

## 预期结果
- 预期 1：新路径下 Docker Desktop 恢复可用
- 预期 2：新路径下 compose 可识别 Dify 服务
- 预期 3：本地 8080 恢复基础 HTTP 入口
- 预期 4：能判断当前本地 Dify 是否已完成 setup，以及是否已有可用 app/token
- 预期 5：`web_demo` 的 lab lane 真正走本地 Dify，而不是 fallback
- 预期 6：页面级展示入口可正常切换并显示关键内容

## 实际结果
- 实际 1：`docker version` 已恢复正常，Docker Desktop engine 可用
- 实际 2：新路径 compose 可识别并显示 `api / db_postgres / redis / web / nginx / ssrf_proxy` 等服务
- 实际 3：宿主机验证通过：`http://127.0.0.1:8080/` 返回 `307 -> /apps`，`http://127.0.0.1:8080/console/api/setup` 返回 `200`
- 实际 4：`http://127.0.0.1:8080/console/api/init` 返回 `200 {"status":"finished"}`，说明当前实例不是未初始化空实例
- 实际 5：数据库验证显示本地已存在 1 个管理员账号、1 个租户、2 个 app、2 个 `api_tokens`
- 实际 6：使用本地现有 app token 直调 `http://127.0.0.1:8080/v1/chat-messages`，`advanced-chat` 与 `chat` 两个 app 均返回 `200`
- 实际 7：新仓库 `web_demo` 当前运行实例的 runtime 指向新路径仓库，且 `chat_lane_lab = Dify 正式知识库工作流`
- 实际 8：`POST /api/chat` with `mode=lab` 返回 `200`，`model = dify-workflow`，说明 lab lane 已接回本地 Dify
- 实际 9：`POST /api/chat` with `mode=agent` 返回 `200`，`model = gpt-5.3-codex`，说明 agent lane 仍保持 OpenAI 兼容直连
- 实际 10：浏览器级回归通过：
  - 侧边栏可切换到“智能问答 / 本地 Dify / 准入阻断”
  - 智能问答页 `lab` 模式页面内显示 `链路=dify-workflow`
  - 智能问答页 `agent` 模式页面内显示 `链路=gpt-5.3-codex`
  - 本地 Dify / 知识库页面显示 `reachable`、`96 条`、`5 条` 等状态
  - 准入阻断页面可继承当前问题上下文
- 实际 11：默认展示 token 已冻结为 `app-wRwHKLfNDGRk4jfCfYeifipT`，对应 app 类型为 `advanced-chat（实验室安全小助手）`
- 实际 12：2026-04-16 第二轮浏览器级回归再次通过：
  - 平台总览页显示 `defense-freeze-20260331`、`已封版 / 20/20`、`Dify 正式知识库工作流`
  - 智能问答页 `lab` 模式再次验证成功，页面内出现 `链路=dify-workflow | 决策=llm_answer_guarded | 规则=R-002 | 风险=高`
  - 智能问答页 `agent` 模式再次验证成功，页面内出现 `链路=gpt-5.3-codex`
  - 本地 Dify / 知识库页面再次显示 `http://127.0.0.1:8080/v1 | timeout=120s`、`reachable`、`96 条`、`5 条`
  - 准入阻断页面再次确认能继承当前问题上下文
- 实际 13：2026-04-16 运行态再次确认：
  - `http://127.0.0.1:8088/api/meta` 返回 `runtime_model = gpt-5.3-codex`
  - `http://127.0.0.1:8080/console/api/setup` 返回 `step = finished`
  - `docker-sandbox-1` 已由此前异常恢复为 `Up ... (healthy)`
- 实际 14：2026-04-16 旧路径默认入口口径清理已完成首轮收口：
  - `run_unified_batch.ps1` 与 `run_pdf_batch_check.ps1` 默认输入根目录已改为 `..\data`
  - 当前 pipeline / ops 现行执行文档示例已切换到 `D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github`
  - `local_workspace_migration_quickstart_cn.md` 中被换行打断的新路径已修复
  - `artifacts/local-web-demo/launch_web_demo_local.ps1` 已不再指向旧 `D:\workspace`
  - 已创建 `D:\newwork\lab-safe-assistant-workspace\data` 作为当前建议资料目录
- 实际 15：聚焦扫描后，剩余旧路径主要集中在：
  - `docs/eval/` 下历史评估报告
  - `docs/ops/v8_2_demo_api_precheck_20260415_cn.md` 这类历史预检记录
  - 当前迁移 change 自身的 proposal / status / verify 中关于“旧路径残留”的说明
  结论：当前默认入口已基本收口，剩余大多属于历史证据或迁移上下文，不宜无差别重写
- 实际 16：2026-04-16 历史报告口径标注收尾已完成：
  - `docs/eval/dify_import_v7_report.md`
  - `docs/eval/failover_status.md`
  - `docs/eval/release_policy_check.md`
  - `docs/eval/release_policy_check_demo.md`
  - `docs/eval/low_confidence_dashboard.md`
  - `docs/ops/go_live_readiness.md`
  - `docs/ops/v8_2_demo_api_precheck_20260415_cn.md`
  以上文档均已补充统一“历史路径说明”，明确旧 `D:\workspace` 仅作历史证据追溯使用


- 实际 17：2026-04-16 已完成“新旧路径口径最终清理”一轮最小收口：
  - `docs/changes/INDEX.md` 已明确当前唯一默认项目根目录为 `D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github`
  - `scripts/README.md`、`docs/README.md`、根 `README.md` 已统一说明旧 `D:\workspace` 不再作为默认执行入口
  - 根 `README.md` 的本地演示运行说明已切换为 `scripts/start_web_demo_local.ps1` / `status_web_demo_local.ps1` / `stop_web_demo_local.ps1`
- 实际 18：2026-04-16 历史运行文档已进一步补齐判定规则：
  - `docs/ops/v8_2_demo_api_precheck_20260415_cn.md` 已明确其中 `D:\workspace\lab-safe-assistant-github\web_demo` 仅为历史执行路径
  - `docs/ops/go_live_readiness.md` 已明确：若历史证据路径与当前入口冲突，以 `docs/README.md`、`AGENTS.md` 与 `scripts/start_web_demo_local.ps1` 为准

## 证据
- 日志：`docker-api-1`、`docker-web-1`、`docker-nginx-1`、`docker-ssrf_proxy-1`
- 输出：`docker version`、`docker compose ps`、HTTP 访问结果、数据库查询结果、`/v1/chat-messages` 返回结果、`/api/chat` 返回结果、浏览器 DOM 快照
- 截图 / 报告：
  - `D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github\artifacts\browser-regression\2026-04-16-platform-overview.png`
  - `D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github\artifacts\browser-regression\2026-04-16-lab-lane.png`
  - `D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github\artifacts\browser-regression\2026-04-16-agent-lane.png`
  - `D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github\artifacts\browser-regression\2026-04-16-dify-workspace.png`
  - `D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github\artifacts\browser-regression\2026-04-16-gate-workspace.png`
- 相关路径：
  - `D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github\local_env\dify\docker\.env`
  - `D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github\local_env\dify\docker\nginx\conf.d\default.conf.template`
  - `D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github\.env.web_demo`
  - `D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github\artifacts\local-web-demo\runtime.json`
  - `D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github\docs\changes\INDEX.md`
  - `D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github\scripts\README.md`
  - `D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github\README.md`
  - `D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github\docs\ops\local_workspace_migration_quickstart_cn.md`
  - `D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github\scripts\run_unified_batch.ps1`
  - `D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github\scripts\run_pdf_batch_check.ps1`
  - `D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github\artifacts\local-web-demo\launch_web_demo_local.ps1`

## 未通过项
- 未通过项 1：未也不计划把历史报告中的旧 `D:\workspace` 全量替换为新路径；当前策略改为补充“历史路径说明”并保留原始证据语义

## 结论
- pass-with-followups
- 是否允许进入下一阶段：
  - 允许继续推进“旧路径口径清理 / 最终演示脚本冻结 / 展示话术冻结”
  - 当前已经允许按新路径进行本地展示与浏览器级演示
