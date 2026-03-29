# V7 在线演示链路执行结果（2026-03-29）

## 1) Dify 知识库导入结果

- 导入文件：`release_exports/v7/knowledge_base_import_ready.csv`
- 数据集：`bf4ab1cd-7d65-44e0-b69f-738b42193f5b`
- 导入结果：`created=350`，`failed=0`
- 报告文件：`artifacts/dify_import_v7/import_report.json`

## 2) 20 题自动回归结果（重跑稳定版）

- 运行目录：`artifacts/eval_smoke_v7_demo_chain_retry/run_20260329_201650`
- 评测条目：`20`
- 关键指标：
  - `safety_refusal_rate = 1.00`（达标）
  - `emergency_pass_rate = 0.80`（未达 0.90）
  - `qa_pass_rate = 0.9091`（达标）
  - `coverage_rate = 0.90`（达标）
  - `latency_p95_ms = 180030.7`（未达 5000）

## 3) 结论

- 链路已打通：`导入 -> Dify 回归` 可以稳定执行。
- 质量状态：正确性已进入可用区间（常规问答和安全拒答达标），但应急与延迟仍需优化。
- 主要瓶颈：个别题目超时（180s）导致 P95 延迟和应急通过率被拉低。
