# 实验安全前置哨（Lab Safety Copilot）— Docker 部署说明

本文档说明如何通过 Docker / Docker Compose 启动当前 no-Dify 轻量 MVP。

## 1. 前置条件

- Docker Engine >= 24
- Docker Compose >= 2.20
- （可选）OpenAI 兼容模型接口
- （可选）Ollama / Embedding 环境

## 2. 快速启动

```bash
git clone https://github.com/leilehuimieba/lab-safety-assistant.git
cd lab-safety-assistant
cp deploy/.env.web_demo.example .env.web_demo
# 如需模型增强，可填写 OPENAI_BASE_URL / OPENAI_API_KEY / OPENAI_MODEL

docker compose up -d
```

默认访问：

- `http://localhost:8088`
- `http://localhost:8088/health`

## 3. 当前环境变量重点

| 变量 | 说明 |
|---|---|
| `DEMO_PORT` | 服务端口，默认 `8088` |
| `ENABLE_EMBEDDING` | 是否启用 embedding，演示建议 `0` |
| `OPENAI_BASE_URL` | OpenAI 兼容接口地址（可选） |
| `OPENAI_API_KEY` | OpenAI 兼容接口 Key（可选） |
| `OPENAI_MODEL` | 默认模型（可选） |

## 4. 演示建议

- 答辩优先使用本地 no-Dify 模式
- 若只展示前端效果，建议打开 `?demo=1`
- 若要展示真实后端逻辑，建议保留 `ENABLE_EMBEDDING=0`，确保响应稳定

## 5. 常用命令

```bash
docker compose logs -f web
docker compose restart web
docker compose down
```
