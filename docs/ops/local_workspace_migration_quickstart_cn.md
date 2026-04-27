# 新工作区迁移说明（Windows）

## 当前默认工作区
- 新工作区根：`D:\newwork\lab-safe-assistant-workspace`
- 主仓库：`D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github`
- 本地 Dify docker 配置：`D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github\local_env\dify\docker`

## 当前默认运行口径
- 本地 Dify 入口：`http://127.0.0.1:8081`
- 本地 web_demo 入口：`http://127.0.0.1:8088`
- 当前 `web_demo` lab lane：`Dify 正式知识库工作流`
- 当前 `web_demo` agent lane：`OpenAI 兼容直连`

## 当前建议工作目录
```powershell
cd D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github
```

## 本地 Dify 配置位置
```powershell
cd D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github\local_env\dify\docker
```

## 当前建议资料目录
```powershell
cd D:\newwork\lab-safe-assistant-workspace\data
```

若暂时还未迁移资料目录，可先按仓库同级 `data` 目录口径整理输入文档。

## web_demo 运行说明
```powershell
powershell -ExecutionPolicy Bypass -File scripts\status_web_demo_local.ps1
```

如需重启：
```powershell
powershell -ExecutionPolicy Bypass -File scripts\stop_web_demo_local.ps1
powershell -ExecutionPolicy Bypass -File scripts\start_web_demo_local.ps1
```

## 说明
- 旧 `D:\workspace` 暂不删除，作为回退点保留。
- 当前已完成“目录与配置内收 + 本地 Dify / web_demo 接回 + 浏览器级展示回归”，仍需继续清理部分历史绝对路径与旧报告口径。

## 默认展示 token
- 当前默认展示 token：`app-wRwHKLfNDGRk4jfCfYeifipT`
- 对应展示 app：`advanced-chat（实验室安全小助手）`
- 若无特殊说明，后续本地演示统一使用该 token 作为默认 `DIFY_APP_API_KEY`。
