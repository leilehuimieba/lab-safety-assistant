# 模拟真实使用场景测试记录

- 生成时间：2026-04-27T11:59:46
- 说明：这是由系统接口真实执行得到的场景试用记录，不是真实用户反馈。

## 学生场景

场景：夜间准备进行乙醇回流实验，审批未闭环，现场只有我一个人，可以开工吗？

操作：
- 提交安全问题
- 查看风险评估
- 生成开工检查
- 提交未满足关键项的清单

实际结果：
- chat_decision: llm_fallback_structured
- risk_level: High
- risk_score: 4
- checklist_items: 9
- allow_start: False
- blocking_reasons: ['SOP, SDS, and experiment objective have been reviewed.', 'Reagent names, concentrations, and labels have been double-checked.', 'Required PPE is available, correctly worn, and suitable for this task.']
- citations: 4

反馈：学生能很快看到不能开工的结论，并知道原因是审批、单人值守和关键检查项未满足。适合实验前自查。

发现问题：
- 部分回答仍偏正式；如果能把“必须联系老师”放到更醒目位置更好。

## 老师场景

场景：查看老师工作台，处理高风险开工申请和培训未通过情况

操作：
- 生成演示管理记录
- 查看管理看板
- 查看待审核和高风险数量
- 导出老师处理清单

实际结果：
- pending_checklists: 3
- high_risk_items: 3
- training_pass_rate: 40%
- incident_open: 1
- report_export_ok: True

反馈：老师能从工作台直接知道先处理哪些事项，导出清单适合留痕。相比单纯问答，更像管理工具。

发现问题：
- 未完成培训人数现在仍依赖记录估算，后续需要接真实班级名单。

## 管理员场景

场景：验收前查看知识库、证据、测试结果和导出材料

操作：
- 查看系统元信息
- 查看知识库状态
- 导出管理周报

实际结果：
- kb_rows: 96
- kb_imported: 398
- low_confidence_queue_count: 0
- formal_eval_score: 20/20
- acceptance_status: 已封版
- admin_report_export_ok: True

反馈：管理员看板能快速回答“知识库多少、测试结果如何、能否导出材料”。适合答辩和阶段验收。

发现问题：
- 还缺一键导出完整验收包；证据链接建议显示已检查可访问数量。
