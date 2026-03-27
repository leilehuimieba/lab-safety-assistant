# V4.2 三条特例结构化重写复检总结（2026-03-27）

## 目标
针对以下 3 条记录，按 `answer/steps/ppe/forbidden/emergency` 强约束模板重写，并提升 `v4_2_recheck` 通过率：

1. `WEBV2-001-001`
2. `WEBV2-012-001`
3. `WEBV3-002-001`

## 主要改写动作
1. 统一改为“结构化执行模板”，避免泛化叙述。
2. `WEBV3-002-001` 重点修复 grounding 风险：
- 问题改为执行型问法（“应如何执行”），避免“条款枚举型”高风险表达。
- 将 `steps` 与条款做一一对应，移除不一致范围引用（如 `D.2.1-D.2.6`）。
- 避免无法核验的直接引文，改为“可核验条款号 + 执行动作”。
3. 三条均补齐 `ppe/forbidden/emergency` 的可执行要点。

## 脚本与输入输出
1. 重写脚本：`scripts/rewrite_v4_2_special_rows.py`
2. 输入：`artifacts/relink_v4_2/relink_success_kb_candidates.csv`
3. 输出：`artifacts/relink_v4_2/relink_success_kb_candidates_structured.csv`

## 审核结果
### Audit（min-score=72）
- 报告：`artifacts/v4_2_template_gate_v4/audit/ai_review_report_audit.json`
- 结果：3/3 通过，`pass_rate=1.0`

### Recheck（min-score=82）
- 报告：`artifacts/v4_2_template_gate_v4/recheck/ai_review_report_recheck.json`
- 结果：3/3 通过，`pass_rate=1.0`

## 结论
V4.2 这三条已完成“强约束结构化模板”修复，当前 audit/recheck 均为全通过，可进入后续发布包整合流程。
