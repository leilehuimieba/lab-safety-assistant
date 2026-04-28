# Design

## 目标概述
- 在不改业务实现的前提下，建立“一个总表 + 多个使用文档”的答辩材料收敛方式。

## 方案概要
- 新增 `docs/ops/defense_alignment_cn.md` 作为答辩口径总入口。
- 更新根 `README.md`，使其适合作为答辩时展示的仓库首页。
- 对 3 分钟演示脚本和答辩话术做最小必要修订，使其统一引用总表。
- 将当前 active change 切换到本任务，并同步路线图当前阶段。

## 关键决策
- 决策 1：以 `v8.2` 和 `formal_acceptance_20260331.md` 作为当前指标口径主证据。
- 决策 2：优先收敛“能稳定讲的能力”，不再扩写超前功能。
- 决策 3：总答辩文档优先级高于单篇脚本和 README。

## 影响模块
- `README.md`
- `docs/ops/defense_alignment_cn.md`
- `docs/ops/demo_script_3min_cn.md`
- `docs/ops/defense_talking_points_cn.md`
- `docs/roadmap.md`
- `docs/changes/INDEX.md`
- `docs/changes/active.txt`

## 对展示主线的影响
- 对演示链路：统一答辩讲法，降低现场口径飘移
- 对门禁 / 验证：复用现有正式验收指标，不新增测试负担
- 对答辩材料：形成一个总入口文档，便于后续继续收敛

## 风险与取舍
- 风险：旧文档较多，短期内仍可能存在历史表述
- 取舍：优先修最关键的四类材料，不一次性全面重写所有答辩文档

## 未决问题
- 最终现场到底走 3 分钟快演还是 5-8 分钟完整版，仍需后续定
- 是否还需要单独准备 PPT 版指标摘要，待后续答辩准备时决定

## 不做项
- 本次不改 `web_demo` 页面功能
- 本次不引入新的答辩图表或 PPT 文件
