# Proposal

## change 名称
2026-04-16-local-server-sync-freeze

## 日期
2026-04-16

## 当前状态
- active

## 背景 / 问题
- 当前本地默认主仓库已经切换到 `D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github`，但服务器侧仍存在“源码目录”和“运行目录”并存的情况：`/root/lab-safe-assistant-github` 与 `/root/lab-safe-assistant-github-release`。
- 本地仓库当前已经比服务器 repo 目录更完整，包含 `docs/changes/`、`docs/templates/`、`local_env/`、`artifacts/` 等结构；如果没有一份统一的目录规划与同步边界说明，后续容易出现“改错目录、同步过量、把本地临时产物推上服务器”的问题。
- 当前项目仍以课程 / 大创展示优先，服务器同步工作的核心目标不是平台化重构，而是确保本地与服务器的目录职责、同步白名单和部署入口都清晰可复现。

## 服务阶段
- Phase 1 - 演示主链路固化

## 目标
- 冻结本地主仓库 / 本地运行层 / 服务器部署层的目录职责边界。
- 给出当前本地与服务器差异对比，并明确哪些内容应同步、哪些内容禁止同步。
- 明确服务器侧唯一推荐部署目录，以及从分叉状态收口到单目录部署的推荐流程。
- 为后续服务器同步、演示部署、答辩说明提供统一执行依据。

## 非目标
- 本次不直接执行服务器实质性迁移或删目录动作。
- 本次不修改 `web_demo` 业务逻辑。
- 本次不处理 prod readiness 阻塞项。
- 本次不重构全部历史部署文档，只做当前主线所需收口。

## 范围
- 包含：
  - `docs/ops/local_server_sync_plan_cn.md`
  - `docs/PROJECT_STRUCTURE.md`
  - `docs/README.md`
  - `docs/roadmap.md`
  - `docs/changes/INDEX.md`
  - 当前 change 文档
- 不包含：
  - 服务器实机目录搬迁
  - 发布脚本逻辑重写
  - Dify 服务器环境改造

## 影响面
- 影响模块：`docs/ops`、`docs/changes`、`docs/PROJECT_STRUCTURE.md`、服务器部署口径
- 影响演示链路：间接影响，主要提升“本地 / 服务器演示环境切换”的可解释性与可复现性
- 影响发布 / 验证链路：影响后续同步方式、部署边界和服务器检查路径

## 验收标准
- [ ] 已建立“本地 / 服务器目录与同步规范”正式文档
- [ ] 已明确本地事实源、本地运行层和服务器部署层的职责边界
- [ ] 已明确同步白名单、黑名单和服务器保留项
- [ ] 已明确服务器当前差异与推荐收口方案
- [ ] 已同步 current active change 与 roadmap / docs 口径

## 风险
- 风险 1：如果服务器现状与文档继续分叉，后续实操同步时仍可能误操作。
- 风险 2：若把本地运行产物错误纳入同步范围，会污染服务器部署目录。

## 回退方案
- 回退点：回退到以 `server_deploy_guide_cn.md` 与现有服务器目录并存方式继续维护。
- 回退条件：若新的同步规范与当前服务器真实运行方式明显冲突，且短期内无法切换到单目录部署。
- 回退步骤：保留本 change 文档作为建议方案，但不切 active，不修改现有部署执行入口。
