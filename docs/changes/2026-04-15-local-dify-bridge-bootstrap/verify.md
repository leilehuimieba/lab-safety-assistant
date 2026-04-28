# Verify

## 验证范围
- 覆盖什么：
  - 本地桥接启动脚本是否能启动 SSH tunnel 与本地 `web_demo`
  - 本地桥接停止脚本是否能清理 tunnel 与 demo 进程
  - 本地 `health` / `meta` 是否可达
  - README 与使用文档是否足够指导复现
- 不覆盖什么：
  - Dify workflow 质量调优
  - 纯本机单机 Dify 部署

## 验证方法
- 命令：
  - 运行 `scripts/run_local_demo_via_server_dify.ps1`
  - 调用 `http://127.0.0.1:<DemoPort>/health`
  - 调用 `http://127.0.0.1:<DemoPort>/api/meta`
  - 按需调用 `http://127.0.0.1:<DemoPort>/api/chat`
- 手工步骤：
  - 浏览器打开本地 bridge 端口
- 场景：
  - Windows 本机，SSH key 可用，服务器 Dify 正常

## 预期结果
- 预期 1：
  - 本地可通过一条命令拉起 tunnel + demo
- 预期 2：
  - health 与 meta 可返回
- 预期 3：
  - 停止脚本可回收运行时进程

## 实际结果
- 实际 1：
  - `scripts/run_local_demo_via_server_dify.ps1` 可成功建立本地 SSH tunnel，并在 `http://127.0.0.1:8091` 拉起 bridge 版 demo
- 实际 2：
  - `http://127.0.0.1:8091/health` 返回 `200` 与 `{"status":"ok"}`
- 实际 3：
  - `http://127.0.0.1:8091/api/meta` 返回 `chat_lane_lab = Dify 正式知识库工作流`
- 实际 4：
  - chat 接口在本轮测试问题上仍返回 `model = fallback-rule-engine`、`decision = llm_fallback_structured`
- 实际 5：
  - `scripts/stop_local_demo_via_server_dify.ps1` 修正 PID 变量冲突后，可正常停止本地 demo 与 SSH tunnel

## 证据
- 日志：
  - `run_local_demo_via_server_dify.ps1` 输出：
    - Demo URL: `http://127.0.0.1:8091`
    - Tunnel URL: `http://127.0.0.1:18081`
- 输出：
  - health: `200 {"status":"ok"}`
  - meta: `chat_lane_lab = Dify 正式知识库工作流`
  - chat: `model = fallback-rule-engine`, `decision = llm_fallback_structured`
- 截图 / 报告：
  - 本轮未额外截图
- 相关路径：
  - `scripts/run_local_demo_via_server_dify.ps1`
  - `scripts/stop_local_demo_via_server_dify.ps1`
  - `docs/ops/local_dify_bridge_quickstart_cn.md`
  - `artifacts/local-dify-bridge/runtime.json`（运行时文件，停止后会清理）

## 未通过项
- 未通过项 1：
  - 本轮测试问题仍未证明远端 Dify workflow 已稳定返回非 fallback 答案

## 结论
- partial
- 是否允许进入下一阶段：
  - 允许作为“本地接服务器 Dify 的最短落地方案”继续使用
  - 但不允许据此宣称“纯本机单机 Dify 已落地”或“所有问答都已稳定走 Dify 正式工作流”
