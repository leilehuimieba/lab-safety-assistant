# Safety Rules Guide

This file explains how to use `safety_rules.yaml` in Dify.

1. Map each rule to a guardrail or conditional block in the workflow.
2. If a rule triggers `refuse`, return a refusal template.
3. If a rule triggers `ask_for_more_info`, request missing details.
4. For emergency-related queries, prefer `redirect_emergency` or specific emergency templates (splash/fire/leak/poisoning).

Emergency keyword rules (suggested priority high -> low)
- 化学品溅到皮肤/眼睛：优先输出冲洗与就医提示
- 起火/冒烟：先停实验、断电气、撤离报警
- 气体泄漏/刺激性气味：撤离通风并报告
- 误食/吸入：立即停止并就医/求助

Recommended Dify flow
- User question
- Rule check (keywords/regex)
- If refused, return safe response
- Else run retrieval from Dataset
- Generate answer with citations
- Post-check for unsafe content

You can expand patterns and add regex rules later.
