# Verify

## 验证范围
- 覆盖什么：本地仓库当前实际目录、服务器 repo 当前实际目录、服务器当前运行目录、同步白名单 / 黑名单 / 保留项规范文档、相关入口文档口径同步，以及 1 次实际服务器同步 / 收口演练与其后续收尾（shell 脚本换行修补、旧 release 目录归档）。
- 不覆盖什么：systemd / nginx 配置切换、同步脚本自动化收口。

## 验证方法
- 命令：
  - `Get-ChildItem -Force <repo-root>`
  - `Get-ChildItem -Directory <repo-root>\docs`
  - `Get-ChildItem -Recurse -Depth 2 <repo-root>\deploy`
  - `Get-ChildItem -Recurse -Depth 2 <repo-root>\web_demo`
  - `Get-ChildItem -Recurse -Depth 2 <repo-root>\scripts`
  - `tar -czf artifacts/deploy_bundle_20260416_2132.tar.gz ...`
  - `scp ... root@175.178.90.193:/root/deploy_bundle_20260416_2132.tar.gz`
  - `ssh root@175.178.90.193 "ps -ef | grep -E 'uvicorn|web_demo.app:app' | grep -v grep"`
  - `ssh root@175.178.90.193 "curl -sS http://127.0.0.1:8088/health"`
  - `ssh root@175.178.90.193 "ss -ltnp | grep 8088"`
  - `ssh root@175.178.90.193 "cd /root/lab-safe-assistant-github && ./deploy/status_web_demo.sh"`
- 手工步骤：
  - 对照 `docs/PROJECT_STRUCTURE.md` 与仓库实际结构
  - 对照 `docs/ops/server_deploy_guide_cn.md` 与服务器实际运行目录
  - 对照新规范文档检查本地 / 服务器差异是否都已落字
  - 在服务器上保留旧 release 目录作为回退点后，切换正式运行目录并验证 health / 进程来源 / 日志
  - 修补本地 `deploy/*.sh` 换行后同步服务器，再验证状态脚本与旧 release 归档状态
- 场景：Windows 本地新工作区 + Ubuntu 服务器实机同步 / 收口演练

## 预期结果
- 预期 1：能明确本地唯一事实源目录
- 预期 2：能明确服务器当前 repo 目录与实际运行目录是否一致
- 预期 3：能明确本地与服务器的主要差异项
- 预期 4：能明确同步白名单、黑名单和服务器保留项
- 预期 5：能明确服务器推荐正式目录与收口流程
- 预期 6：能完成 1 次把 8088 从旧 release 目录切换到正式目录的实操演练
- 预期 7：能修复服务器正式目录中 shell 状态脚本的 Linux 兼容性，并把旧 release 目录归档

## 实际结果
- 实际 1：本地唯一默认事实源已明确为 `D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github`
- 实际 2：服务器初始存在 `/root/lab-safe-assistant-github` 与 `/root/lab-safe-assistant-github-release` 两套目录
- 实际 3：服务器切换前 `web_demo` 实际运行于 `/root/lab-safe-assistant-github-release`
- 实际 4：服务器切换前 `http://127.0.0.1:8088/health` 返回 `{"status":"ok"}`，说明旧 release 目录可用
- 实际 5：本地仓库当前比服务器 repo 目录更完整，新增了 `docs/changes/`、`docs/templates/`、`local_env/`、`artifacts/` 等内容
- 实际 6：已建立新规范文档，明确：
  - 主仓库层
  - 本地运行层
  - 服务器部署层
  - 服务器历史快照层
  - 同步白名单 / 黑名单 / 服务器保留项
  - 推荐同步流程与验证清单
- 实际 7：已从本地主仓库打出最小部署包：`artifacts/deploy_bundle_20260416_2132.tar.gz`
- 实际 8：已将最小部署包上传到服务器：`/root/deploy_bundle_20260416_2132.tar.gz`
- 实际 9：已把服务器原 `/root/lab-safe-assistant-github` 备份到：`/root/backups/lab-safe-assistant-github_before_sync_`
- 实际 10：已把最小部署包解压到新的正式目录 `/root/lab-safe-assistant-github`，且该目录已包含：
  - `docs/changes/`
  - `docs/templates/`
  - `web_demo/data/`
  - 最新 `deploy/` / `scripts/` / `release_exports/`
- 实际 11：已把服务器现用 `.env.web_demo` 从 `/root/lab-safe-assistant-github-release/.env.web_demo` 复制到 `/root/lab-safe-assistant-github/.env.web_demo`
- 实际 12：已从 `/root/lab-safe-assistant-github` 启动 `web_demo`
- 实际 13：当前监听 `8088` 的进程为：
  - `/root/lab-safe-assistant-github/.venv/bin/python3 .venv/bin/uvicorn web_demo.app:app --host 0.0.0.0 --port 8088`
  说明 8088 已由正式目录接管
- 实际 14：`ss -ltnp | grep 8088` 显示当前端口 8088 归属于新正式目录进程 pid `1609834`
- 实际 15：`http://127.0.0.1:8088/health` 再次返回 `{"status":"ok"}`，说明切换后服务正常
- 实际 16：旧 release 目录再次尝试启动时，日志返回 `address already in use`，反向证明新正式目录已接管 8088
- 实际 17：已修复本地 `deploy/` 下 4 个 CRLF shell 脚本，并同步到服务器正式目录
- 实际 18：服务器正式目录中的 `status_web_demo.sh`、`start_public_tunnel.sh`、`status_public_tunnel.sh`、`stop_public_tunnel.sh` 已确认为 LF
- 实际 19：服务器执行 `cd /root/lab-safe-assistant-github && ./deploy/status_web_demo.sh` 已能正常输出：
  - `[运行中] PID=1609834`
  - `http://127.0.0.1:8088/health`
  - `{"status":"ok"}`
- 实际 20：旧 release 目录已归档为：`/root/lab-safe-assistant-github-release-archived-20260416_2145`

## 证据
- 日志：
  - `/root/lab-safe-assistant-github/logs/web_demo.log`
  - `/root/lab-safe-assistant-github-release-archived-20260416_2145/logs/web_demo.log`
- 输出：
  - 本地目录扫描输出
  - 服务器 `find ~/lab-safe-assistant-github -maxdepth 2`
  - 服务器 `curl http://127.0.0.1:8088/health`
  - 服务器 `ps -ef | grep uvicorn`
  - 服务器 `ss -ltnp | grep 8088`
  - 服务器 `cd /root/lab-safe-assistant-github && ./deploy/status_web_demo.sh`
- 截图 / 报告：
  - 无
- 相关路径：
  - `artifacts/deploy_bundle_20260416_2132.tar.gz`
  - `artifacts/deploy_sh_fix_20260416_2145.tar.gz`
  - `docs/ops/local_server_sync_plan_cn.md`
  - `docs/PROJECT_STRUCTURE.md`
  - `docs/ops/server_deploy_guide_cn.md`
  - `docs/ops/local_dify_bridge_quickstart_cn.md`
  - `docs/ops/systemd_web_demo_guide_cn.md`
  - `docs/changes/INDEX.md`
  - `docs/changes/active.txt`

## 未通过项
- 未通过项 1：尚未把本次服务器收口沉淀成自动化同步脚本

## 结论
- pass
- 是否允许进入下一阶段：
  - 允许切回 `2026-04-14-v8-2-demo-flow-freeze` 继续主讲人口播计时彩排与最终 freeze gate 盖章
