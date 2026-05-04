# Safety Rules Guide（no-Dify 规则引擎）

当前 `safety_rules.yaml` 不再主要用于 Dify workflow 条件块，而是作为 no-Dify MVP 的本地确定性安全规则库。

## 1. 规则定位

规则引擎负责在模型调用前识别高风险模式，承担安全边界：

```text
用户输入 / 实验场景
  -> normalize / keyword pattern
  -> match_rule
  -> refuse / redirect_emergency / ask_for_more_info / safe_answer
  -> 再进入知识库检索或模型生成
```

原则：

1. 高危规则必须优先于 LLM。
2. 能确定阻断的场景不要交给模型自由判断。
3. 模型只能辅助解释、摘要和生成检查项，不能承担最终安全许可。
4. 规则命中后应返回结构化字段，便于前端渲染三色决策卡和审核包。

## 2. 常见动作

| action | 用途 |
|---|---|
| `refuse` | 高危、违法或明显不可开工场景，直接拒绝危险指导并给出安全替代建议 |
| `redirect_emergency` | 已发生事故或紧急场景，转到应急卡片 |
| `ask_for_more_info` | 缺 SOP/SDS/PPE/通风/老师批准等关键条件，需要补充信息 |
| `safe_answer` | 可给一般安全说明，但仍需带来源和保守提示 |

## 3. 推荐规则优先级

1. 事故已发生：火灾、泄漏、触电、灼伤、误吸入、误食等。
2. 明显高危组合：易燃溶剂 + 明火 / 加热，强氧化剂 + 有机物，金属钠 + 水等。
3. 缺关键条件：未读 SOP/SDS，未穿 PPE，通风不可用，单人高风险操作，未获老师批准。
4. 一般风险提醒：常规 PPE、废液、标签、应急设备确认。

## 4. 维护要求

每条规则建议至少包含：

- `id`
- `severity`
- `patterns`
- `action`
- `response`
- 可选：`hazard_types`、`required_checks`、`suggested_ppe`

新增规则后必须验证：

```powershell
python -m pytest -q
```

并至少手工检查一个高风险主链路：

```text
输入高风险场景 -> 风险等级 High/Critical -> 检查清单 -> 缺关键项阻断 -> 老师审核
```

## 5. Dify 兼容说明

历史文档中曾建议把规则映射到 Dify workflow guardrail。该方式仍可作为旧 v8.2 演示或外部平台兼容方案，但当前主线以本地 Python 规则引擎为准。
