# 发布风险说明（自动）

- 生成时间：`2026-03-29T09:56:34+08:00`
- 门禁判定：`WARN_ONLY`
- 最新 Smoke 运行：`run_20260329_095243`

## 1) 最新链路与质量快照

| 指标 | 当前值 | 目标值 |
|---|---:|---:|
| 链路可用率 | 100.0% | 70.0% |
| 超时率 | 0.0% | 30.0% |
| 安全拒答率 | 100.0% | 95.0% |
| 应急合格率 | 40.0% | 90.0% |
| 常规问答合格率 | 36.4% | 85.0% |
| 模糊问答合格率 | 0.0% | 80.0% |

## 2) 门禁违规项

- route_success_rate failed for 2 consecutive weeks (target=0.7, 2026-W12:0.0000, 2026-W13:0.3425)

## 3) 临时豁免信息

- 模式：`warn_only`
- 生效开始：`2026-03-28`
- 生效结束：`2026-04-11`
- 原因：live regression route metric recovering after SSE timeout and model-channel stabilization
- 关联单号：OPS-20260328-LIVE-ROUTE-RECOVERY
- 审批人：project-owner

## 4) 发布建议

- 建议：可临时发布（告警放行），需在下个周期关闭链路风险。

- JSON 明细：`D:\workspace\lab-safe-assistant-github\docs\eval\release_risk_note_auto.json`
