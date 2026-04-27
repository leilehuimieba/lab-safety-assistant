# Windows 本地 web_demo 启动说明

## 目标
- 用统一脚本启动当前仓库版本的 `web_demo`
- 避免继续手工在不明目录里执行 `uvicorn app:app`
- 为后续继续接本地 Dify 留出稳定入口

## 第一步：准备环境文件
在仓库根目录检查是否存在：

- `.env.web_demo`

如果不存在，可先复制：

```powershell
Copy-Item .env.web_demo.example .env.web_demo
```

至少配置其一：

- `DIFY_APP_API_KEY`
- `OPENAI_API_KEY`

> 当前如果本机没有 Dify，可先仅填写 `OPENAI_API_KEY`，让 demo 先跑起来；实验室问答会处于“结构化回退模式”。

## 第二步：启动

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_web_demo_local.ps1
```

成功后默认地址：

- `http://127.0.0.1:8088`

## 第三步：查看状态

```powershell
powershell -ExecutionPolicy Bypass -File scripts/status_web_demo_local.ps1
```

## 第四步：停止

```powershell
powershell -ExecutionPolicy Bypass -File scripts/stop_web_demo_local.ps1
```

## 当前说明
- 如果本机 `127.0.0.1:8081` 没有 Dify，则 `/api/meta` 中会显示：
  - `Dify 未配置，当前处于结构化回退模式`
- 这不影响前端工作台和知识库抽查功能的本地开发
- 后续若要切到真正本地 Dify，只需补：
  - `DIFY_BASE_URL`
  - `DIFY_APP_API_KEY`
