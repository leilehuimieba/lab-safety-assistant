# 项目文档总入口

这里是实验室安全助手项目的材料入口，答辩、验收、测试和后续待办都从这里找。

## 1. 答辩演示材料

| 用途 | 文件 |
|---|---|
| 老师工作台答辩演示说明 | `docs/demo/teacher_workbench_defense_demo.md` |
| 产品优化方案 | `docs/product/product_optimization_plan_20260426.md` |

建议现场演示顺序：

1. 打开首页
2. 点“老师演示模式”
3. 点“答辩演示下一步”
4. 看老师工作台
5. 导出老师处理清单
6. 切到管理员模式，看“课题验收看板”

---

## 2. 验收材料

| 用途 | 文件 |
|---|---|
| Go-live 预检结论 | `docs/ops/go_live_readiness.md` |
| 发布准备看板 | `docs/eval/release_readiness_dashboard.md` |
| 发布策略检查 | `docs/eval/release_policy_check.md` |
| 稳定性检查 | `docs/eval/release_stability_check.md` |
| 失败摘要 | `docs/ops/go_live_failure_digest_latest.md` |

验收时优先看：

1. `docs/ops/go_live_readiness.md`
2. `docs/eval/release_readiness_dashboard.md`
3. `docs/eval/release_stability_check.md`

---

## 3. 测试与评测材料

| 用途 | 文件 |
|---|---|
| 评测看板 | `docs/eval/eval_dashboard.md` |
| 发布阻断项 | `docs/eval/release_blocker_topn.md` |
| 风险说明 | `docs/eval/release_risk_note_auto.md` |
| 故障转移状态 | `docs/eval/failover_status.md` |

当前自动测试命令：

```powershell
python -m pytest -q
```

当前最近一次检查结果：`154 passed`。

---

## 4. 数据与知识库材料

| 用途 | 文件 |
|---|---|
| 主知识库 | `knowledge_base_curated.csv` |
| 发布导入包 | `release_exports/v8.2/knowledge_base_import_ready.csv` |
| 数据源与抓取材料 | `docs/pipeline/` |

管理员演示时重点讲：

1. 知识库条目数量
2. 证据链接可追溯
3. 测试结果可导出
4. 管理周报可下载


---

## 5. 试点反馈材料

| 用途 | 文件 |
|---|---|
| 单人试用反馈表 | `docs/pilot/pilot_feedback_form.md` |
| 多人反馈汇总表 | `docs/pilot/pilot_feedback_summary.md` |

使用建议：

1. 先找 3-5 个学生/老师试用；
2. 每人填一份反馈表；
3. 再把结果汇总到反馈汇总表；
4. 最后作为课题验收材料。

---

## 6. 项目待办

| 用途 | 文件 |
|---|---|
| 唯一待办总表 | `docs/reports/UNIFIED_TODO_BOARD.md` |

后续优先处理：

1. 补真实试点反馈
2. 老师/学生/管理员真实账号权限
3. 培训未完成人员改为真实名单
4. 继续清洗低质量来源

---

## 7. 运行入口

启动演示服务：

```powershell
cd web_demo
python -m uvicorn app:app --host 127.0.0.1 --port 8101
```

打开：

```text
http://127.0.0.1:8101/
```

健康检查：

```text
http://127.0.0.1:8101/health
```
