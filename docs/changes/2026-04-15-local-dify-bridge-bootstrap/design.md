# Design

## 目标概述
- 本设计服务于“先把本地可提交的 Dify 版运行路径落地”这个目标。

## 方案概要
- 一句话方案：
  - 在 Windows 本机启动 `web_demo`，但通过 SSH 隧道把本地 `DIFY_BASE_URL` 指向腾讯云服务器上的 Dify。
- 主流程：
  1. 通过 SSH 建立 `127.0.0.1:<TunnelPort> -> 服务器 127.0.0.1:8080` 隧道
  2. 从服务器 `.env.web_demo` 读取 `DIFY_APP_API_KEY`（仅在进程内使用，不落盘）
  3. 用临时环境变量启动本地 `web_demo`
  4. 本地访问 `http://127.0.0.1:<DemoPort>`，完成 health / meta / chat 验证

## 关键决策
- 决策 1：
  - 不在本次 change 中重建 Windows 本地 Dify，而是优先走“本地入口 + 服务器 Dify 后端”的最短闭环。
- 决策 2：
  - 默认本地 bridge 端口使用 `8090`，避免与当前已经在跑的本地 `8088` 冲突。
- 决策 3：
  - 脚本默认不把远端 `DIFY_APP_API_KEY` 写入仓库文件，只在运行时注入环境变量。
- 决策 4：
  - 启动与停止分成两个 PowerShell 脚本，避免用户手工找 PID。

## 影响模块
- 模块 / 文档 / 脚本：
  - `scripts/run_local_demo_via_server_dify.ps1`
  - `scripts/stop_local_demo_via_server_dify.ps1`
  - `docs/ops/local_dify_bridge_quickstart_cn.md`
  - `README.md`
  - `docs/changes/*`
- 影响方式：
  - 新增一条面向 Windows 本地演示的运行路径，不影响现有服务器部署脚本与业务逻辑

## 对展示主线的影响
- 对演示链路：
  - 允许用户在本机浏览器里跑一个“接服务器 Dify”的版本，便于提交和展示
- 对门禁 / 验证：
  - 增加 health / meta / chat 三类最小验证动作
- 对答辩材料：
  - 可把运行口径收敛为“本地前端入口，Dify 后端使用已落地服务器环境”

## 风险与取舍
- 风险：
  - 该方案仍依赖外部服务器网络连通与远端 Dify 状态
- 取舍原因：
  - 当前目标是最短落地，不是完整本机基础设施重建

## 未决问题
- 问题 1：
  - 是否后续还要继续推进“纯本机单机 Dify 环境”作为下一阶段任务
- 问题 2：
  - 是否需要进一步补“本地桥接模式下的 chat probe 自动验证”

## 不做项
- 本次明确不覆盖：
  - `web_demo` 业务逻辑改造
  - 服务器 Dify workflow 重配
  - Windows Docker / Dify 全量安装文档
