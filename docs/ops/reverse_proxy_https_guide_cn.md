# 反向代理与 HTTPS 上线指南（Nginx / Caddy）

目标：把 `web_demo` 从 `127.0.0.1:8088` 暴露成可公网访问的域名，并启用 HTTPS。

## 1. 前置条件

1. `web_demo` 已在服务器本机运行并可探活：

```bash
curl -sS http://127.0.0.1:8088/health
```

2. 已有域名（例如 `lab-safe.example.com`）并解析到服务器公网 IP。

3. 服务器放行 80/443 端口。

## 2. 方案 A：Nginx（模板）

模板文件：

- `deploy/nginx/lab-safe-assistant.conf.template`

将模板中的占位符替换：

- `__DOMAIN__` -> 你的域名
- `__DEMO_PORT__` -> 演示端口（默认 8088）

然后放到 Nginx 配置目录并重载。

> HTTPS 证书可配合 Certbot 申请并自动续期。

## 3. 方案 B：Caddy（推荐简化）

模板文件：

- `deploy/caddy/Caddyfile.template`

将占位符替换后作为 `Caddyfile` 使用：

- `__DOMAIN__` -> 你的域名
- `__DEMO_PORT__` -> 演示端口（默认 8088）

Caddy 会自动申请和续期 HTTPS 证书（前提是 DNS 与端口开放正确）。

## 4. 上线后核验清单

1. `https://<你的域名>/health` 返回 `{"status":"ok"}`
2. 页面可正常打开，问答接口可调用
3. 一键预检通过：

```bash
python scripts/release/go_live_preflight.py \
  --repo-root . \
  --release-dir release_exports/v8.1 \
  --web-health-url https://<你的域名>/health
```

## 5. 安全建议（上线必须）

1. 仅开放必要端口（80/443）
2. 设置基础限流（每 IP 每分钟请求阈值）
3. 记录访问日志并保留近 30 天
4. 对管理接口做访问控制（IP 白名单或认证）
