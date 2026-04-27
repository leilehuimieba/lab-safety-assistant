# Status

## 当前状态
- done

## 当前步骤
- 已完成“本地 / 服务器目录与同步规范”文档落地，并已按规范完成 1 次服务器同步 / 收口演练。
- 当前服务器 8088 已稳定由正式目录 `/root/lab-safe-assistant-github` 接管；旧 release 目录已归档为历史快照。

## 已完成
- 已读取项目结构、服务器部署、go-live readiness、本地桥接和 systemd 部署等相关文档
- 已确认本地默认事实源为 `D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github`
- 已确认本地仓库当前额外包含：`docs/changes/`、`docs/templates/`、`local_env/`、`artifacts/`、`logs/`、`output/`
- 已通过 SSH 只读确认服务器存在两套目录：
  - `/root/lab-safe-assistant-github`
  - `/root/lab-safe-assistant-github-release`
- 已确认服务器切换前 `web_demo` 实际运行目录为 `/root/lab-safe-assistant-github-release`
- 已确认服务器切换前 `http://127.0.0.1:8088/health` 返回 `{"status":"ok"}`
- 已确认服务器 repo 目录下的 `docs/` 结构比本地仓库更旧，未包含当前 change 治理层
- 已落地正式规范文档：`docs/ops/local_server_sync_plan_cn.md`
- 已更新 `docs/PROJECT_STRUCTURE.md`，把主仓库层 / 本地运行层 / 服务器部署层 / 服务器历史快照层写入正式结构规范
- 已更新 `docs/README.md`，补充本地 / 服务器目录与同步口径入口
- 已更新 `docs/roadmap.md`，把“本地 / 服务器同步与部署边界规范”纳入当前 Phase 1 目标与交付物
- 已切换 active change：
  - `docs/changes/INDEX.md`
  - `docs/changes/active.txt`
- 已将 `2026-04-14-v8-2-demo-flow-freeze` 调整为 paused，保留其后续“主讲人口播计时彩排”待办
- 已完成 1 次服务器同步 / 收口演练：
  - 已从本地主仓库打最小部署包 `artifacts/deploy_bundle_20260416_2132.tar.gz`
  - 已上传到服务器 `/root/deploy_bundle_20260416_2132.tar.gz`
  - 已备份服务器原 `/root/lab-safe-assistant-github` 到 `/root/backups/lab-safe-assistant-github_before_sync_`
  - 已将最小部署包解压到 `/root/lab-safe-assistant-github`
  - 已把服务器现用 `.env.web_demo` 从 release 目录复制回正式目录
  - 已从正式目录启动 `web_demo`
  - 已确认当前监听 `8088` 的进程来自 `/root/lab-safe-assistant-github/.venv/bin/python3`
  - 已确认新正式目录 `http://127.0.0.1:8088/health` 返回 `{"status":"ok"}`
  - 已确认旧 release 目录再次启动时因端口占用失败，说明 8088 已被新正式目录接管
- 已修复本地 `deploy/` 下 4 个仍为 CRLF 的 shell 脚本，并同步到服务器正式目录：
  - `deploy/status_web_demo.sh`
  - `deploy/start_public_tunnel.sh`
  - `deploy/status_public_tunnel.sh`
  - `deploy/stop_public_tunnel.sh`
- 已验证服务器正式目录中的以上脚本均为 LF，且 `./deploy/status_web_demo.sh` 可在 Linux 下正常执行
- 已将旧目录归档为：`/root/lab-safe-assistant-github-release-archived-20260416_2145`

## 未完成
- 尚未把本次服务器切换沉淀成自动化同步脚本
- 尚未恢复 `2026-04-14-v8-2-demo-flow-freeze` 继续主讲人口播计时彩排

## 阻塞
- 当前无硬阻塞

## 下一步
1. 若继续推进演示主线，切回 `2026-04-14-v8-2-demo-flow-freeze`，补主讲人口播计时彩排与 freeze gate 盖章
2. 如需长期运维，再考虑新增统一同步脚本和服务器 smoke check 脚本
3. 如需更彻底的平台化，再考虑 systemd / nginx / go-live 路径收口

## 最近更新时间
- 2026-04-16 21:48
