# MVP 快速入门（no-Dify）

本指南面向当前主线：`实验安全前置哨 / Lab Safety Copilot` 的 no-Dify 自研轻量 MVP。

旧的 Dify Dataset / workflow 启动方式已经不再作为当前主线。当前目标是本地 FastAPI + 本地知识库 + YAML 规则 + 可选模型直连完成实验前安全检查闭环。

## 1. 最小闭环

```text
学生输入实验场景
  -> 规则引擎和知识库识别风险
  -> 生成开工前检查清单
  -> 缺关键项则阻断
  -> 高风险进入老师审核
  -> 管理看板统计
```

## 2. 核心文件

| 文件 | 用途 |
|---|---|
| `web_demo/app.py` | FastAPI 入口 |
| `web_demo/routers/` | API 路由 |
| `web_demo/services/` | 风险、问答、审核、看板等业务逻辑 |
| `web_demo/frontend/` | Vite + TypeScript + Tailwind 前端 |
| `knowledge_base_curated.csv` | 本地知识库 |
| `safety_rules.yaml` | 安全规则 |
| `artifacts/` | 运行时记录 |
| `docs/ops/no_dify_mvp_acceptance_checklist.md` | 当前验收清单 |

## 3. 本地启动

```powershell
cd D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github
$env:ENABLE_EMBEDDING="0"
python -m uvicorn web_demo.app:app --host 127.0.0.1 --port 8088
```

浏览器访问：

```text
http://127.0.0.1:8088
```

## 4. 关键验收点

1. 高风险实验能被评为 High / Critical。
2. 未勾选 SOP / PPE / 老师批准等关键项时，系统返回 `allow_start=false`。
3. 阻断原因明确展示。
4. 老师审核包能看到风险和缺失项。
5. 管理看板能看到待审核、风险和低置信问题。
6. 不配置 Dify 时主链路仍可运行。

## 5. 当前建议

- 当前默认只围绕 no-Dify 本地主链路推进
- 演示时优先使用 `http://127.0.0.1:8088/?demo=1`
- 如需继续扩展，应优先补齐主链路验收、答辩截图与测试证据
