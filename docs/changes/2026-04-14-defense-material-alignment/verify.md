# Verify

## 验证范围
- 验证答辩材料是否已统一到相同项目名、版本基线和指标口径
- 验证主要答辩文档是否已指向统一总表
- 验证是否已提供“提交版 / 展示版最小交付清单”，便于课程提交或老师快速查看
- 验证是否已提供“高频追问快答版”，便于临场 15 - 30 秒回答老师追问
- 不覆盖业务接口运行测试

## 验证方法
- 手工检查以下文档：
  - `README.md`
  - `docs/ops/defense_alignment_cn.md`
  - `docs/ops/submission_minimum_delivery_cn.md`
  - `docs/ops/defense_faq_quick_answers_cn.md`
  - `docs/ops/demo_script_3min_cn.md`
  - `docs/ops/demo_script.md`
  - `docs/ops/demo_freeze_runbook_cn.md`
  - `docs/ops/defense_talking_points_cn.md`
  - `docs/roadmap.md`
- 对照现有证据文档：
  - `docs/eval/formal_acceptance_20260331.md`
  - `docs/eval/v8_2_release_summary.md`
- 对照现有页面与接口能力：
  - `web_demo/templates/index.html`
  - `web_demo/app.py`

## 预期结果
- 预期 1：项目名称统一为“实验室安全小助手”
- 预期 2：当前展示基线统一为 `v8.2`
- 预期 3：核心指标统一为 `398 / 20/20 / 3/3 PASS`
- 预期 4：答辩话术不再明显超出现有页面 / 接口 / 验收证据

## 实际结果
- 实际 1：根 README 和答辩文档已统一使用“实验室安全小助手”
- 实际 2：当前展示基线已统一到 `v8.2`
- 实际 3：核心指标已统一
- 实际 4：答辩总表已明确“不要超讲的内容”
- 实际 5：5-8 分钟完整版脚本已统一到当前总口径
- 实际 6：演示顺序和异常切换策略已冻结成独立 runbook
- 实际 7：已新增“提交版 / 展示版最小交付清单”，并接入答辩总表与 README 导航，便于老师快速查看最小必看材料
- 实际 8：已新增“高频追问快答版”，覆盖“和普通 AI 区别 / 创新点 / 为什么先云端模型 / 是否可上线 / 事故复盘为何不进主线 / 当前最大短板”等高频问题

## 证据
- 文档证据：
  - `README.md`
  - `docs/ops/defense_alignment_cn.md`
  - `docs/ops/submission_minimum_delivery_cn.md`
  - `docs/ops/defense_faq_quick_answers_cn.md`
  - `docs/ops/demo_script_3min_cn.md`
  - `docs/ops/demo_script.md`
  - `docs/ops/demo_freeze_runbook_cn.md`
  - `docs/ops/defense_talking_points_cn.md`
  - `docs/roadmap.md`
- 背景证据：
  - `docs/eval/formal_acceptance_20260331.md`
  - `docs/eval/v8_2_release_summary.md`
  - `web_demo/app.py`
  - `web_demo/templates/index.html`

## 未通过项
- 无

## 结论
- pass
- 允许继续进入下一轮答辩材料细化或演示链路固化
