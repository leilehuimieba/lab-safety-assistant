# Proposal

## change 名称
2026-04-15-workspace-migration-to-newwork

## 日期
2026-04-15

## 当前状态
- active

## 背景 / 问题
- 当前项目主仓库位于 `D:\workspace\lab-safe-assistant-github`，本地 Dify 配置分散在 `D:\workspace\_misc\dify\docker`。
- 用户希望把工作区迁移到 `D:\newwork`，并把 Dify 相关配置一起收进一个项目文件夹，减少路径分散和后续运维混乱。

## 服务阶段
- 当前阶段：Phase 1 - 演示主链路固化

## 目标
- 建立 `D:\newwork` 下新的项目工作区。
- 复制当前仓库到新路径，并保持旧 `D:\workspace` 作为回退点。
- 把本地 Dify docker 配置内收进项目目录，建立统一入口。

## 非目标
- 本次不直接重做全部历史产物路径。
- 本次不立即清理旧 `D:\workspace`。
- 本次不保证所有历史绝对路径文档一次性全部替换。

## 范围
- 包含：仓库复制、Dify 配置迁入、最小脚本/文档同步、可运行性验证。
- 不包含：历史评估产物批量重写、服务器侧部署改造。

## 影响面
- 影响模块：`scripts/`、`docs/`、本地 Dify docker 配置目录。
- 影响演示链路：影响本地启动入口与本地 Dify 路径。
- 影响发布 / 验证链路：影响本地验证命令和后续维护口径。

## 验收标准
- [ ] `D:\newwork` 下存在新的项目工作区
- [ ] 主仓库可从新路径读取与启动
- [ ] 本地 Dify 配置已进入项目目录内
- [ ] 至少一条新路径启动/验证说明已补齐

## 风险
- 风险 1：旧文档中仍有 `D:\workspace` 绝对路径残留。
- 风险 2：Dify 运行态与 WSL / Docker Desktop 状态可能继续干扰迁移验证。

## 回退方案
- 回退点：保留旧 `D:\workspace\lab-safe-assistant-github` 和旧 Dify 目录。
- 回退条件：新路径运行失败或关键脚本不可用。
- 回退步骤：停止新路径实例，切回旧路径继续运行。
