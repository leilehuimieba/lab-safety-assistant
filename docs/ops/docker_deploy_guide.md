# LabSafe Assistant — Docker 产品化部署指南

本文档说明如何通过 Docker / Docker Compose 一键部署 LabSafe Assistant，适用于开发测试、演示环境及生产环境。

---

## 前置条件

- [Docker Engine](https://docs.docker.com/engine/install/) >= 24.0
- [Docker Compose](https://docs.docker.com/compose/install/) >= 2.20（或 `docker compose` 插件）
- （可选）已安装 [Ollama](https://ollama.com) 并拉取了 `bge-m3` 模型，用于本地 Embedding 语义检索

---

## 快速开始（3 步启动）

```bash
# 1. 克隆仓库
git clone https://github.com/leilehuimieba/lab-safety-assistant.git
cd lab-safety-assistant

# 2. 复制并编辑环境配置
cp deploy/.env.web_demo.example .env.web_demo
# 编辑 .env.web_demo，填入 DIFY_APP_API_KEY 和 OPENAI_API_KEY

# 3. 启动服务
docker compose up -d

# 4. 查看状态
docker compose ps
docker compose logs -f web
```

服务启动后访问：
- Web 服务：`http://localhost:8088`
- 健康检查：`http://localhost:8088/health`
- 搜索接口：`http://localhost:8088/api/search?q=实验室着火怎么办`

---

## 环境变量说明

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DIFY_BASE_URL` | `http://127.0.0.1:8080` | Dify API 地址 |
| `DIFY_APP_API_KEY` | — | Dify 应用 API Key（**必填**） |
| `DIFY_TIMEOUT` | `120` | Dify 请求超时（秒） |
| `OPENAI_BASE_URL` | — | OpenAI 兼容接口地址 |
| `OPENAI_API_KEY` | — | OpenAI 兼容接口 Key |
| `OPENAI_MODEL` | `gpt-5.2-codex` | 默认模型 |
| `DEMO_PORT` | `8088` | 服务监听端口 |
| `EMBEDDING_BACKEND` | `ollama` | Embedding 后端：`ollama` 或 `sentence-transformers` |
| `EMBEDDING_MODEL` | `bge-m3` | Embedding 模型名称 |
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | Ollama 服务地址（容器内访问宿主机） |

---

## Ollama 配置（推荐）

### 方式一：宿主机运行 Ollama（推荐）

在宿主机上安装 Ollama 并拉取模型：

```bash
ollama pull bge-m3
ollama serve
```

容器通过 `host.docker.internal:11434` 访问宿主机 Ollama，无需额外配置。

### 方式二：容器内运行 Ollama（独立部署）

如需完全容器化，可在 `docker-compose.yml` 中添加 Ollama 服务：

```yaml
services:
  ollama:
    image: ollama/ollama:latest
    container_name: lab-safe-ollama
    volumes:
      - ollama-data:/root/.ollama
    ports:
      - "11434:11434"
    networks:
      - lab-safe-net

  web:
    # ... 原有配置
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
```

---

## 常用运维命令

```bash
# 查看日志
docker compose logs -f web

# 重启服务
docker compose restart web

# 停止并删除容器
docker compose down

# 停止并删除容器+卷（清空调试运行数据）
docker compose down -v

# 进入容器调试
docker compose exec web bash

# 手动构建镜像（不启动）
docker build -t lab-safe-assistant:latest .

# 导出镜像
docker save lab-safe-assistant:latest | gzip > lab-safe-assistant.tar.gz
```

---

## 生产环境建议

### 1. 使用 Nginx 反向代理 + HTTPS

取消 `docker-compose.yml` 中 `nginx` 服务的注释，并配置 SSL 证书：

```bash
# 准备证书
mkdir -p deploy/nginx/ssl
cp your-cert.pem deploy/nginx/ssl/cert.pem
cp your-key.pem deploy/nginx/ssl/key.pem

# 启动
docker compose up -d nginx
```

### 2. 自动更新镜像

配置 Watchtower 或手动拉取最新镜像：

```bash
docker compose pull
docker compose up -d
```

### 3. 数据备份

```bash
# 备份知识库、日志和配置
tar czvf lab-safe-backup-$(date +%Y%m%d).tar.gz \
  knowledge_base_curated.csv \
  safety_rules.yaml \
  .env.web_demo \
  logs/ \
  artifacts/ \
  .cache/
```

---

## 镜像 CI/CD

项目已配置 GitHub Actions 自动构建镜像：

- **触发条件**：push 到 `main`、打 `v*` 标签、或手动触发
- **目标仓库**：`ghcr.io/leilehuimieba/lab-safety-assistant`
- **多架构**：支持 `linux/amd64` 和 `linux/arm64`

使用预构建镜像启动（无需本地 build）：

```bash
docker pull ghcr.io/leilehuimieba/lab-safety-assistant:main
docker run -d -p 8088:8088 --env-file .env.web_demo ghcr.io/leilehuimieba/lab-safety-assistant:main
```

---

## 故障排查

| 现象 | 可能原因 | 解决 |
|------|---------|------|
| 容器启动后立即退出 | `.env.web_demo` 缺失或配置错误 | 检查环境文件是否存在 |
| `/health` 返回 502 | 服务尚未完成启动 | 等待 10~30 秒（首次启动需构建 Embedding 索引） |
| 语义检索失效 | Ollama 未启动或模型未下载 | 检查 `ollama list` 和 `ollama serve` |
| 镜像构建慢 | sentence-transformers 依赖 torch | 使用多阶段构建已优化，首次较慢属正常 |

---

## 与裸机部署对比

| 维度 | Docker 部署 | 裸机部署（systemd） |
|------|------------|-------------------|
| 环境隔离 | ✅ 完全隔离 | ❌ 依赖宿主机 Python |
| 一键启动 | ✅ `docker compose up -d` | 需手动配置 systemd |
| 跨平台 | ✅ 任意支持 Docker 的系统 | 主要面向 Ubuntu |
| 镜像体积 | ~1.5GB（含 torch） | 无额外镜像 |
| 适合场景 | 生产、演示、云原生 | 开发、资源受限环境 |
