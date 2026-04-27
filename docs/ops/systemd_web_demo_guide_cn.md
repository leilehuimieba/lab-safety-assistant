# Web Demo Systemd 常驻部署（用户态）

适用场景：你希望 `web_demo` 在服务器上长期稳定运行，并具备自动重启能力。

## 1. 准备

在仓库根目录确保有环境文件：

```bash
cp deploy/.env.web_demo.server.example .env.web_demo
vi .env.web_demo
```

至少配置：

- `OPENAI_BASE_URL`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `DEMO_PORT`（默认 8088）

## 2. 安装并启动用户态 systemd 服务

```bash
chmod +x deploy/install_web_demo_systemd.sh deploy/uninstall_web_demo_systemd.sh
./deploy/install_web_demo_systemd.sh
```

默认服务名：`lab-safe-assistant-web-demo.service`

## 3. 常用运维命令

```bash
systemctl --user status lab-safe-assistant-web-demo.service
systemctl --user restart lab-safe-assistant-web-demo.service
journalctl --user -u lab-safe-assistant-web-demo.service -f
```

探活：

```bash
curl -sS http://127.0.0.1:8088/health
```

## 4. 卸载服务

```bash
./deploy/uninstall_web_demo_systemd.sh
```

## 5. 参数化安装（可选）

通过环境变量自定义：

```bash
SERVICE_NAME=lab-safe-web \
REPO_DIR=$HOME/lab-safe-assistant-github \
ENV_FILE=$HOME/lab-safe-assistant-github/.env.web_demo \
./deploy/install_web_demo_systemd.sh
```

## 6. 常见问题

1. `systemctl --user` 不可用  
   原因：系统未启用用户会话 systemd。  
   处理：改用 `deploy/start_web_demo.sh` 先运行，后续再切换到 systemd。

2. 服务启动后立即退出  
   处理：查看日志 `journalctl --user -u lab-safe-assistant-web-demo.service -n 100`，通常是 `OPENAI_API_KEY` 未配置或端口冲突。

3. 重启后服务未自动恢复  
   处理：确认执行过 `systemctl --user enable --now ...`。如宿主机策略限制用户服务，需改为系统级 service（管理员模式）。
