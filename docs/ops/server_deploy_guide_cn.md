# 线上演示部署指南（Ubuntu 服务器）

本文档用于把项目中的在线演示页面部署到 Linux 服务器，支持：

- 页面展示
- 调用“项目协作智能体”
- 调用“实验室安全小助手”

当前方案是“用户态部署”，不依赖 sudo，可快速上线演示。

## 1. 部署结构
部署目录建议：

- `~/lab-safe-assistant-github/`
- 演示程序：`web_demo/`
- 启停脚本：`deploy/start_web_demo.sh` `deploy/stop_web_demo.sh` `deploy/status_web_demo.sh`

服务端口：

- 默认 `8088`
- 访问地址示例：`http://<服务器IP>:8088`

## 2. 首次部署步骤
## 2.1 上传代码
由于仓库可能是私有仓库，推荐在本地打包后上传：

```bash
# 本地执行（Windows PowerShell）
cd D:\workspace\lab-safe-assistant-github
tar -czf deploy_bundle.tar.gz web_demo deploy docs scripts data_sources README.md
scp deploy_bundle.tar.gz youruser@<服务器IP>:~/
```

## 2.2 服务器解压

```bash
ssh youruser@<服务器IP>
mkdir -p ~/lab-safe-assistant-github
tar -xzf ~/deploy_bundle.tar.gz -C ~/lab-safe-assistant-github
cd ~/lab-safe-assistant-github
```

## 2.3 配置环境变量

```bash
cp deploy/.env.web_demo.example .env.web_demo
vi .env.web_demo
```

至少配置：

- `OPENAI_BASE_URL`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `OPENAI_FALLBACK_MODELS`
- `DEMO_PORT`

建议先检查中转站可用模型再填写 `OPENAI_MODEL`：

```bash
curl -s http://ai.little100.cn:3000/v1/models \
  -H "Authorization: Bearer <你的key>"
```

## 2.4 启动服务

```bash
chmod +x deploy/*.sh
./deploy/start_web_demo.sh
./deploy/status_web_demo.sh
```

若显示 `{"status":"ok"}` 说明服务正常。

## 3. 日常运维命令
启动：

```bash
./deploy/start_web_demo.sh
```

停止：

```bash
./deploy/stop_web_demo.sh
```

状态检查：

```bash
./deploy/status_web_demo.sh
```

看日志：

```bash
tail -f logs/web_demo.log
```

上线前一键体检（推荐每次发布前执行）：

```bash
chmod +x deploy/go_live_preflight.sh
./deploy/go_live_preflight.sh
```

体检报告产物：

- `docs/ops/go_live_readiness.json`
- `docs/ops/go_live_readiness.md`

判断规则：

- `overall=PASS`：可进入发布窗口。
- `overall=WARN`：建议先处理告警再发布。
- `overall=BLOCK`：禁止发布，先处理阻断项。

## 3.1 公网端口未放行时的临时方案（推荐演示用）
如果你暂时不能开安全组端口（如 8088），可以使用 Cloudflare 临时隧道：

```bash
chmod +x deploy/start_public_tunnel.sh deploy/stop_public_tunnel.sh deploy/status_public_tunnel.sh
./deploy/start_public_tunnel.sh
./deploy/status_public_tunnel.sh
```

脚本会输出一个 `https://xxxxx.trycloudflare.com` 地址，可直接用于演示。

停止隧道：

```bash
./deploy/stop_public_tunnel.sh
```

## 4. 常见问题排查
问题：服务启动失败，日志提示缺少 key。  
处理：检查 `.env.web_demo` 中 `OPENAI_API_KEY` 是否配置。

问题：本机能访问，外网无法访问。  
处理：检查云服务器安全组/防火墙是否放行 `8088` 端口；若暂时无法放行，改用临时隧道脚本。

问题：返回 502。  
处理：上游模型服务不可达、模型名不可用或响应格式不兼容。先查 `/v1/models`，再调整 `OPENAI_MODEL` 与 `OPENAI_FALLBACK_MODELS`。

## 5. 可选增强（后续）
- 增加 Nginx/Caddy 反向代理（443 + 域名）
- 增加 Basic Auth 登录保护
- 接入 Dify App API，切换为“知识库驱动”的正式问答链路

## 6. 推荐生产化增强（新增）

1. systemd 常驻运行（用户态）  
   参考：`docs/ops/systemd_web_demo_guide_cn.md`  
   可用脚本：`deploy/install_web_demo_systemd.sh`

2. 反向代理与 HTTPS  
   参考：`docs/ops/reverse_proxy_https_guide_cn.md`  
   模板：
   - `deploy/nginx/lab-safe-assistant.conf.template`
   - `deploy/caddy/Caddyfile.template`

3. 上线前稳定性验收（连续 3 轮）  
   参考：`scripts/run_release_stability_check.ps1`
