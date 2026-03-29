# 发布风险说明（自动）

- 生成时间：`2026-03-29T15:08:26+08:00`
- 门禁判定：`WARN_ONLY`
- 最新 Smoke 运行：`run_20260329_130447`

## 1) 最新链路与质量快照

| 指标 | 当前值 | 目标值 |
|---|---:|---:|
| 链路可用率 | 0.0% | 70.0% |
| 超时率 | 100.0% | 30.0% |
| 安全拒答率 | 0.0% | 95.0% |
| 应急合格率 | 0.0% | 90.0% |
| 常规问答合格率 | 0.0% | 85.0% |
| 模糊问答合格率 | 0.0% | 80.0% |

## 2) Failover 状态

- 最新结果：`fail`
- 最新时间：`2026-03-29T06:42:10+00:00`
- 最终模型：`gpt-5.2-codex`
- 触发原因：`primary canary timeout ratio reached threshold (1.00 >= 1.00)`
- 最近窗口统计：PASS=0, DEGRADED=0, FAIL=9

## 3) 门禁违规项

- route_success_rate failed for 2 consecutive weeks (target=0.7, 2026-W12:0.0000, 2026-W13:0.5475)
- latest failover result is fail with streak=9 (threshold=2)

## 4) 临时豁免信息

- 模式：`warn_only`
- 生效开始：`2026-03-28`
- 生效结束：`2026-04-11`
- 原因：live regression route metric recovering after SSE timeout and model-channel stabilization
- 关联单号：OPS-20260328-LIVE-ROUTE-RECOVERY
- 审批人：project-owner

## 5) 发布建议

- 建议：告警放行（临时豁免），需在下个周期关闭链路风险。

## 6) 文件索引

- 风险说明 JSON：`D:\workspace\lab-safe-assistant-github\docs\eval\release_risk_note_auto.json`
- failover 状态：`D:\workspace\lab-safe-assistant-github\docs\eval\failover_status.json`
