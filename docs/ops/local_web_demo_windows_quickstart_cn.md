# Windows 本地启动说明（当前版本）

适用项目：**实验安全前置哨（Lab Safety Copilot）**

## 1. 目标

在 Windows 本地快速启动当前 no-Dify Web 应用，用于开发、调试、答辩演示和截图。

## 2. 推荐启动方式

```powershell
cd D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github
powershell -ExecutionPolicy Bypass -File scripts/start_web_demo_local.ps1
```

默认地址：

- `http://127.0.0.1:8088`

## 3. 演示模式

如需使用前端 mock 数据进行答辩展示：

- `http://127.0.0.1:8088/?demo=1`

退出演示模式：

- `http://127.0.0.1:8088/?demo=0`

## 4. 手工调试方式

```powershell
$env:ENABLE_EMBEDDING="0"
python -m uvicorn web_demo.app:app --host 127.0.0.1 --port 8088
```

## 5. 当前说明

- 当前主链路默认不依赖 Dify
- 如配置了上游模型接口，可用于增强问答能力
- 演示与答辩优先使用本地可运行链路
