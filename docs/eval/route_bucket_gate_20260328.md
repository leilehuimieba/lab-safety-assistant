# response_route 分桶看板与门禁说明（2026-03-28）

## 目标

把评测问题拆成两类：

1. 上游链路问题（网关/模型超时、通道不可用）
2. 模型质量问题（拒答、应急、常规问答质量）

避免“链路故障导致质量门误判”。

## 看板新增项

`generate_eval_dashboard.py` 已新增并输出以下链路指标（按 `response_route` 聚合）：

- `route_success_rate`：链路可用率（primary/fallback 且有效回答）
- `route_fallback_rate`：降级命中率
- `route_primary_rate`：主通道命中率
- `route_failure_rate`：链路失败率
- `route_timeout_rate`：超时率

## 门禁策略（新版）

`validate_eval_dashboard_gate.py` 现在分两层判定：

1. 路由健康门（先判）
   - `route_success_rate >= 0.70`
   - `route_timeout_rate <= 0.30`
   - 连续 2 周不达标则直接阻止发布

2. 质量门（后判）
   - 仅在“链路可用周”（`route_success_rate >= 0.70`）上评估质量指标
   - 若没有足够的链路可用周，质量门会被跳过，不再误判

## 你要怎么读结果

- 如果门禁报 `route_success_rate` / `route_timeout_rate` 失败：先修上游链路，不要急着改知识库。
- 如果链路门通过但质量门失败：再进入提示词、知识库与规则库调优。
