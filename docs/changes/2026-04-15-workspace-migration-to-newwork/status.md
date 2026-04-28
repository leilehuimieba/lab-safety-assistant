# Status

## 当前状态
- paused

## 当前步骤
- 新工作区迁移主线已基本完成，当前让位于 `2026-04-14-v8-2-demo-flow-freeze` 作为主推进 change。
- 本 change 进入“按点修复旧路径误导入口 / 保留历史证据说明”的跟随收尾状态，不再作为默认执行入口。

## 已完成
- 已确认新主仓库路径为 `D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github`
- 已将本地 Dify docker 配置内收到新仓库 `local_env/dify/docker`
- 已重新拉起 Docker Desktop，并确认 `docker version` 恢复正常
- 已在新路径下执行 compose 检查，确认 `api / db_postgres / redis / web / nginx / ssrf_proxy` 主要容器可见
- 已修复新路径下 nginx 两个直接问题：
  - 补回 `nginx/conf.d/default.conf.template`
  - 将 `.env` 中 `EXPOSE_NGINX_PORT/EXPOSE_NGINX_SSL_PORT` 收口为 `8080/8443`
- 已确认本地 Dify 宿主机入口恢复：
  - `http://127.0.0.1:8080/` 返回 `307 -> /apps`
  - `http://127.0.0.1:8080/console/api/setup` 返回 `200`
  - `http://127.0.0.1:8080/console/api/init` 返回 `200`
- 已确认本地 Dify 不是未初始化空实例：数据库中已存在 1 个管理员、1 个租户、2 个 app、2 个 app token
- 已确认现有两枚本地 app token 均可成功调用 `/v1/chat-messages`
- 已确认新仓库 `.env.web_demo` 已配置 `DIFY_BASE_URL=http://127.0.0.1:8080` 与本地有效 `DIFY_APP_API_KEY`
- 已确认新路径 `web_demo` 当前运行实例就是新仓库实例：runtime 指向 `D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github`
- 已冻结默认展示 token：`app-wRwHKLfNDGRk4jfCfYeifipT`，对应展示 app：`advanced-chat（实验室安全小助手）`
- 已完成新路径 `web_demo` 接回验证：
  - `/api/meta` 显示 `chat_lane_lab = Dify 正式知识库工作流`
  - `mode=lab` 提问返回 `model = dify-workflow`
  - `mode=agent` 提问仍返回 `model = gpt-5.3-codex`
- 已完成浏览器级展示回归：
  - 侧边栏可切换到智能问答 / 本地 Dify / 准入阻断页面
  - 智能问答页 `lab` 模式可在页面内返回 Dify 结果
  - 智能问答页 `agent` 模式可在页面内返回 `gpt-5.3-codex` 结果
  - 本地 Dify / 知识库页可显示 `reachable`、知识条目数、低置信积压等状态
  - 准入阻断页能继承当前问题上下文
- 已完成 2026-04-16 第二轮浏览器级展示回归并补截图证据
- 已完成 2026-04-16 一轮旧路径默认入口口径清理
- 已完成 2026-04-16 一轮“新旧路径口径最终清理”
- 已完成 2026-04-16 一轮历史报告口径标注收尾

## 未完成
- 尚未也不计划把新路径同步到全部历史证据文档；当前已完成对默认入口文档的最终收口
- 后续仅在发现新的误导性旧路径入口时按点修复

## 阻塞
- 当前阻塞 1：迁移 change 自身与少量历史文档仍会保留旧 `D:\workspace` 作为历史上下文说明

## 下一步
1. 若后续仍发现误导性入口文档，再按点修复，不做全仓盲改
2. 若演示主链路冻结完成后需要回补迁移口径，再同步服务器侧或历史文档说明

## 最近更新时间
- 2026-04-16 20:35
