# Design

## 目标概述
- 把“本地主仓库、 本地运行层、服务器部署层、服务器历史快照层”的职责拆清楚，并收敛成一份可直接执行的同步规范。

## 方案概要
- 一句话方案：以本地新工作区仓库作为唯一事实源，把服务器收敛为“单正式部署目录 + 可选历史快照目录”，并用同步白名单 / 黑名单保护边界。
- 主流程：
  1. 盘点本地实际目录与服务器实际目录。
  2. 建立标准分层：主仓库层 / 本地运行层 / 服务器部署层 / 服务器历史快照层。
  3. 给出同步白名单、黑名单和服务器保留项。
  4. 给出推荐收口路径：服务器正式目录统一到 `/root/lab-safe-assistant-github`，`/root/lab-safe-assistant-github-release` 仅保留为快照或回退点。

## 关键决策
- 决策 1：`D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github` 是当前唯一默认事实源。
- 决策 2：服务器侧只应有一个正式运行目录，推荐统一为 `/root/lab-safe-assistant-github`。
- 决策 3：`local_env/`、`artifacts/`、`logs/`、`output/`、`.venv*`、`_tmp_*` 属于本地运行层，不进入服务器标准同步包。
- 决策 4：服务器自己的 `.env.web_demo`、日志、run 目录、systemd / nginx / caddy 实际配置副本应保留在服务器，不由本地覆盖。

## 影响模块
- 模块 / 文档 / 脚本：
  - `docs/ops/local_server_sync_plan_cn.md`
  - `docs/PROJECT_STRUCTURE.md`
  - `docs/README.md`
  - `docs/roadmap.md`
  - `docs/changes/INDEX.md`
  - `docs/changes/active.txt`
- 影响方式：统一本地 / 服务器目录口径和同步边界；不改业务代码。

## 对展示主线的影响
- 对演示链路：减少“本地能演、服务器目录混乱”的不确定性，方便答辩时解释本地与服务器的关系。
- 对门禁 / 验证：后续服务器 smoke check、deploy 和 go-live 预检的目标目录更明确。
- 对答辩材料：能稳定回答“本地项目和服务器项目有什么区别，怎么同步”的高频问题。

## 风险与取舍
- 风险：如果现在直接收服务器目录，可能影响现有运行服务。
- 取舍原因：本次先冻结规范，不直接搬迁服务器目录；先用文档把边界和步骤写死，再决定何时执行切换。

## 未决问题
- 问题 1：服务器何时从 `/root/lab-safe-assistant-github-release` 切回 `/root/lab-safe-assistant-github` 正式运行。
- 问题 2：后续服务器同步采用 tar/scp 还是 rsync 作为标准流程，是否另起脚本收口。

## 不做项
- 本次明确不覆盖：
  - 服务器目录实迁
  - `web_demo` 功能改造
  - Dify 服务器侧重配
