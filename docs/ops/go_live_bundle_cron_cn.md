# Go-Live Bundle 每日定时任务（Cron）

## 目的

将 `deploy/run_server_go_live_bundle.sh` 设置为每日自动执行，持续产出：

- `docs/ops/go_live_bundle_latest.json/.md`
- `docs/ops/go_live_failure_digest_latest.json/.md`
- `docs/ops/runtime_profile_snapshot.json/.md`

## 脚本

- 安装：`deploy/install_go_live_bundle_cron.sh`
- 查看：`deploy/status_go_live_bundle_cron.sh`
- 卸载：`deploy/uninstall_go_live_bundle_cron.sh`

## 快速安装

```bash
cd /root/lab-safe-assistant-github
chmod +x deploy/install_go_live_bundle_cron.sh deploy/status_go_live_bundle_cron.sh deploy/uninstall_go_live_bundle_cron.sh
CRON_SCHEDULE="20 2 * * *" ./deploy/install_go_live_bundle_cron.sh deploy/env/go_live_bundle.env
./deploy/status_go_live_bundle_cron.sh
```

说明：

- 默认每天 `02:20` 执行。
- 可通过 `CRON_SCHEDULE` 覆盖，例如：
  - `CRON_SCHEDULE="0 */6 * * *"`（每 6 小时一次）

## 日志位置

- 默认日志：`artifacts/go_live_bundle/cron_daily.log`
- 可通过环境变量 `LOG_FILE` 自定义。

## 卸载

```bash
cd /root/lab-safe-assistant-github
./deploy/uninstall_go_live_bundle_cron.sh
./deploy/status_go_live_bundle_cron.sh
```

## 建议

- 每次改动 `deploy/env/go_live_bundle.env` 后，手动先跑一次 bundle，再观察下一次 cron 结果。
- 若连续出现 `BLOCK`，优先看 `docs/ops/go_live_failure_digest_latest.md` 的根因摘要。
