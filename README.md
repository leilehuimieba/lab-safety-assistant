# 实验安全前置哨（Lab Safety Copilot）

面向高校实验教学和科研实验场景的轻量级**实验前安全决策系统**。

当前项目已经完成从“Dify/RAG 问答演示”向 **no-Dify 自研轻量 MVP** 的主线切换。现在的核心目标不是单纯回答安全知识，而是帮助学生在实验开始前判断：

> 当前条件下，这个实验**能不能开工**；如果不能，**缺什么**；如果风险高，**是否必须老师确认**。

---

## 1. 当前统一命名

- **正式中文名**：实验安全前置哨
- **正式英文名**：Lab Safety Copilot
- **中文说明名**：实验前安全检查助手

答辩、文档、页面标题和产品介绍统一使用以上口径。

---

## 2. 当前项目阶段

- 当前阶段：`Phase 5 - no-Dify 需求重定位与轻量 MVP`
- 当前 active change：`docs/changes/2026-04-28-demand-realignment-no-dify/`
- 当前主线：**实验前自查 → 风险判断 → 开工阻断 / 老师确认 → 管理看板**

---

## 3. 当前 P0 能力

1. 安全问答 / 实验场景输入
2. 风险识别与风险等级判断
3. 开工前检查清单生成
4. 阻断规则（暂不可开工 / 需老师确认）
5. 老师工作台
6. 管理看板
7. 应急卡片
8. 培训考核
9. 系统状态与运行验证

---

## 4. 当前关键入口

| 类型 | 路径 | 说明 |
|---|---|---|
| 文档总入口 | `docs/README.md` | 当前唯一执行入口 |
| 文档索引 | `docs/INDEX.md` | 当前保留文档总览 |
| 路线图 | `docs/roadmap.md` | 当前阶段与下一步 |
| active change | `docs/changes/2026-04-28-demand-realignment-no-dify/` | 当前推进状态 |
| 产品文档 | `docs/product/` | PRD、需求、设计、API、测试、答辩材料 |
| 运行文档 | `docs/ops/` | 本地启动、Docker、验收清单、演示脚本 |
| 前端源码 | `web_demo/frontend/` | Vite + TypeScript + Tailwind |
| 后端入口 | `web_demo/app.py` | FastAPI 服务 |

---

## 5. 本地运行

### 启动

```powershell
cd D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github
powershell -ExecutionPolicy Bypass -File scripts/start_web_demo_local.ps1
```

默认地址：

- `http://127.0.0.1:8088`

### 演示模式（Mock 数据）

- `http://127.0.0.1:8088/?demo=1`

### 停止

```powershell
powershell -ExecutionPolicy Bypass -File scripts/stop_web_demo_local.ps1
```

---

## 6. 当前答辩建议展示路径

1. 首页 / 安全问答
2. 开工检查
3. 阻断结果（暂不可开工）
4. 老师工作台
5. 管理看板
6. 系统状态

---

## 7. 当前原则

- 不再把 Dify 作为当前主线依赖
- 不再以 v8.2 演示链路作为当前事实源
- 不再以申报书补材料作为当前开发主线
- 当前仓库只保留**现在在做、现在要讲、现在要验收**的材料

---

## 8. 下一步

- 补齐 MVP 主链路验收
- 补齐答辩截图与讲稿
- 将剩余测试修到全绿
- 继续围绕真实实验场景打磨演示质量
