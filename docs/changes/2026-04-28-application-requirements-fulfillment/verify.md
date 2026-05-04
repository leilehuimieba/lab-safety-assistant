# Verify

## 验证范围
- 覆盖申报书需求整理是否完成。
- 覆盖当前项目能力与申报书目标的差距是否明确。
- 覆盖本 change 工作区是否完整。
- 不覆盖 1000/3000 条知识库实际完成情况。
- 不覆盖真实试点反馈实际完成情况。

## 验证方法
- 手工检查：
  - 旧申报书兑现版需求文档（已删除，申报书主线暂停；必要时从 Git 历史恢复）
  - 旧申报书差距矩阵（已删除，申报书主线暂停；必要时从 Git 历史恢复）
  - `docs/changes/2026-04-28-application-requirements-fulfillment/proposal.md`
  - `docs/changes/2026-04-28-application-requirements-fulfillment/design.md`
  - `docs/changes/2026-04-28-application-requirements-fulfillment/tasks.md`
  - `docs/changes/2026-04-28-application-requirements-fulfillment/status.md`
  - `docs/changes/2026-04-28-application-requirements-fulfillment/verify.md`
  - `docs/changes/INDEX.md`
  - `docs/changes/active.txt`
- 数据对照：
  - `knowledge_base_curated.csv`
  - `release_exports/v8.2/knowledge_base_import_ready.csv`
  - `eval_set_v1.csv`

## 预期结果
- 预期 1：申报书四大模块被转成工程需求。
- 预期 2：申报书指标被转成可验收口径。
- 预期 3：当前已完成与未完成事项被清楚区分。
- 预期 4：后续 P0 任务明确指向 1000/3000 条知识库、评测指标和真实试点。
- 预期 5：本 change 可作为后续推进入口。

## 实际结果
- 实际 1：已新增申报书兑现版需求规格说明。
- 实际 2：已新增申报书目标与当前项目差距矩阵。
- 实际 3：已建立完整 change 五件套。
- 实际 4：已把本 change 设为当前 active change。
- 实际 5：已明确当前不能宣称完成申报书全部目标，下一步需先补数据规模、评测和试点证据。

## 证据
- 旧申报书兑现版需求文档（已删除，申报书主线暂停；必要时从 Git 历史恢复）
- 旧申报书差距矩阵（已删除，申报书主线暂停；必要时从 Git 历史恢复）
- `docs/changes/2026-04-28-application-requirements-fulfillment/`
- `docs/changes/INDEX.md`
- `docs/changes/active.txt`
- 申报书提取中间文件：`D:\newwork\lab-safe-assistant-workspace\data\standard_from_doc_utf8.txt`

## 未通过项
- 未通过项 1：申报书最终目标尚未全部完成，尤其是 ≥3000 条知识库、真实试运行、7×24 证据和部分指标。

## 结论
- partial
- 允许进入下一阶段：`v9.0-core-1000` 知识库扩容与申报书指标评测落地。
