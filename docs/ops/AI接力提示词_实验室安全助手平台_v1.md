# 可直接发给下一个 AI 的提示词（复制即用）

你现在是本项目的接力开发 AI，请在 `D:\workspace\lab-safe-assistant-github` 仓库继续工作。  
目标是推进“实验室安全助手平台”，要求以 AI 辅助自动化为主、人工为辅。

## 项目目标

1. 实现实验室安全问答平台：针对常规安全问题给出基于知识库的回答。
2. 数据处理全链路自动化：采集 -> 清洗 -> 入库 -> 评测 -> 门禁 -> 风险说明。
3. 所有数据必须可追溯（来源链接/来源文件必须保留）。
4. 当前技术策略：先用云端 API 跑通，后续再迁移本地模型。

## 你必须先做的事情

1. 先读取并理解：
   - `docs/ops/AI交接包_实验室安全助手平台_20260328.md`
   - `docs/ops/runbook.md`
   - `docs/eval/eval_dashboard.md`
2. 执行仓库健康检查：
   - `git status`
   - `pytest`
3. 输出当前状态摘要：已完成能力 / 风险 / 下一步任务建议（最多 5 条）。

## 执行风格要求

1. 每轮按“Task 文本 -> 直接执行 -> 回报结果”节奏推进。
2. 优先做可落地改动，不要只给方案不执行。
3. 每次重要改动后要提交并推送 GitHub（`main`）。
4. 避免破坏性命令；如果有冲突先说明再处理。

## 当前重点待办（优先级顺序）

1. 数据源扩充与可追溯补齐（官方/高校/规范类优先）。
2. 评测集 V2 扩容（覆盖常规/拒答/应急/模糊提问）。
3. 按门禁失败聚类自动生成修复任务，并反馈到文档看板。
4. 完善 web_demo 接入，确保团队可在线演示。
5. 预备本地模型 A/B 影子评估（暂不直接切换生产）。

## 关键脚本入口

- `scripts/run_eval_regression_pipeline.py`
- `scripts/validate_eval_dashboard_gate.py`
- `scripts/generate_release_risk_note.py`
- `scripts/generate_weekly_gate_ops.py`
- `scripts/web_ingest_pipeline.py`
- `scripts/unified_kb_pipeline.py`

## 配置约束

1. 不使用 Apifox。
2. 使用现有 GitHub Actions / 脚本体系继续演进。
3. 需要的 Secrets / Variables 见交接文档第 6 节。

## 交付格式（每轮）

1. 本轮 Task 名称
2. 已执行改动（文件列表）
3. 验证结果（命令 + 通过/失败）
4. Git 提交信息（commit id）
5. 下一轮建议 Task
