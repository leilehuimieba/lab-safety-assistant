# no-Dify MVP 验收清单

> 适用阶段：Phase 5 - no-Dify 需求重定位与轻量 MVP  
> 适用 change：`docs/changes/2026-04-28-demand-realignment-no-dify/`  
> 目标：验证当前项目不依赖 Dify 也能完成“实验前自查 -> 阻断 -> 老师审核 -> 管理看板”的最小闭环。

## 1. 验收前置条件

- [ ] 当前工作目录为 `D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github`
- [ ] 本地依赖已安装
- [ ] `ENABLE_EMBEDDING=0` 时服务可快速启动
- [ ] `knowledge_base_curated.csv` 存在
- [ ] `safety_rules.yaml` 存在
- [ ] `web_demo/frontend/dist/` 存在或可重新构建

推荐启动命令：

```powershell
cd D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github
$env:ENABLE_EMBEDDING="0"
python -m uvicorn web_demo.app:app --host 127.0.0.1 --port 8088
```

## 2. API 级验收

### 2.1 健康检查

- [ ] `GET /health` 返回 200
- [ ] `GET /api/meta` 返回版本和知识库状态
- [ ] `GET /api/admin/dashboard` 返回 200

### 2.2 风险评估

高风险输入示例：

```text
锂电池拆解，使用金属螺丝刀撬开外壳，未阅读 SOP，未穿绝缘手套，未获得老师批准。
```

期望：

- [ ] `POST /api/risk/assess` 返回 200
- [ ] `risk_score >= 4` 或 `risk_level` 为 High / Critical
- [ ] `key_hazards` 包含 Electrical / Fire 或相关危险类型
- [ ] 返回 PPE 建议和禁止事项

### 2.3 检查清单生成

- [ ] `POST /api/checklist/template` 返回基础检查项
- [ ] 高风险场景追加老师批准 / 双人核对类检查项
- [ ] 电气 / 火灾相关场景追加专项检查项

### 2.4 阻断判定

提交时故意不勾选 SOP、PPE、老师批准等关键项。

期望：

- [ ] `POST /api/checklist/submit` 返回 200
- [ ] `allow_start=false`
- [ ] `blocking_reasons` 非空，且能指出具体缺失项
- [ ] `review_status=pending`
- [ ] 写入 `artifacts/checklists/checklist_runs.csv`

### 2.5 老师审核

- [ ] 老师工作台或相关接口能看到 pending 记录
- [ ] `PATCH /api/checklist/{id}/review` 可批准或驳回
- [ ] 审核后记录包含 `reviewed_by`、`reviewed_at`、`review_comment`

### 2.6 本地知识库问答

- [ ] `POST /api/chat` 在无 Dify 配置时仍可返回结构化 fallback 或本地检索答案
- [ ] 专业安全问题返回 `citations`
- [ ] 命中危险规则时不调用模型硬答

### 2.7 低置信队列

使用知识库明显不足的问题，例如：

```text
某个非常具体的新型纳米材料复合涂层在等离子体处理时的特殊安全参数是什么？
```

期望：

- [ ] 返回 `low_confidence=true` 或保守提示
- [ ] 不给出无依据的危险操作建议
- [ ] 写入 `artifacts/low_confidence_followups/data_gap_queue.csv`
- [ ] 管理看板能展示低置信问题摘要

## 3. 浏览器级验收

访问：`http://127.0.0.1:8088`

至少走查以下页面：

- [ ] 首页 / 总览
- [ ] 实验前自查或检查清单页
- [ ] 风险决策结果页
- [ ] 老师审核工作台
- [ ] 管理看板
- [ ] 安全问答页
- [ ] 应急卡片页（P1，可选）
- [ ] 培训页（P1，可选）

## 4. 自动化测试 Gate

- [ ] `python -m pytest -q` 通过
- [ ] 如果仍有 `test_eval_smoke.py` 失败，必须在交付说明中单独列出原因和修复计划
- [ ] `python scripts/quality_gate.py --repo-root . --skip-secret-scan` 可运行并输出明确结论

## 5. 通过标准

当前 no-Dify MVP 可宣布通过的最低标准：

1. 不配置 Dify 的情况下，Web 服务可启动。
2. 高风险场景能被识别为 High / Critical。
3. 缺关键检查项时 `allow_start=false`。
4. 阻断原因具体、可理解。
5. 高风险/阻断记录能进入老师审核。
6. 老师可以批准或驳回。
7. 管理看板可看到待审核、高风险或低置信相关统计。
8. 专业问答尽量带来源；低置信时不硬答。

## 6. 推荐验收记录格式

```text
验收日期：
验收人：
代码提交：
启动方式：
Dify 是否配置：否 / 是（可选）
Embedding 是否启用：否 / 是
pytest 结果：
高风险阻断结果：
老师审核结果：
管理看板结果：
低置信队列结果：
结论：PASS / PARTIAL / FAIL
遗留问题：
```
