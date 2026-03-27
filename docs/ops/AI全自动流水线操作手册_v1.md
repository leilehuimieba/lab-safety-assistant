# AI全自动流水线操作手册 v1

目标：在“先不做人工审核”的阶段，实现从收集到入库的全 AI 闭环。

## 1. 对应关系（你的 10 步）

1. 全部 AI 审核：`scripts/ai_review_kb.py --stage audit`
2. AI 通过：自动生成 `knowledge_base_audit_pass.csv`
3. AI 复检：`scripts/ai_review_kb.py --stage recheck`
4. AI 收集数据：`scripts/unified_kb_pipeline.py`（文档+网页）
5. AI 入库：`scripts/run_ai_oneclick_pipeline.py` 自动 merge
6. 一键 AI：`scripts/run_ai_oneclick.ps1`
7. 检查脚本：`scripts/validate_ai_pipeline_report.py`
8. AI 复查：同一轮内自动二次复检（recheck）
9. 后期人工核查：保留 `docs/eval/release_review_log.md` 流程，后续再启用
10. 持续加强：看“第 6 节”

## 2. 一键执行

在仓库根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_ai_oneclick.ps1 `
  -DocumentInputRoot "D:\workspace\data" `
  -WebManifest "data_sources\web_seed_urls_v4_candidates.csv" `
  -WebFetcherMode "auto" `
  -AuditMinScore 72 `
  -RecheckMinScore 82 `
  -StrictHighRisk `
  -AllowSkipLiveEval
```

说明：

- `AllowSkipLiveEval`：当 Dify 凭据未配置时，允许跳过在线回归，不会整轮失败。
- 若要只跑小样本验证，可加 `-ReviewLimit 20`。

## 3. 环境变量（必须）

```powershell
$env:OPENAI_BASE_URL="http://ai.little100.cn:3000/v1"
$env:OPENAI_API_KEY="你的中转站apikey"
$env:OPENAI_MODEL="gpt-5.2-codex"
```

可选：

```powershell
$env:OPENAI_FALLBACK_MODELS="grok-3-mini,grok-4,grok-3"
$env:OPENAI_TIMEOUT="60"
```

## 4. 产物说明

每次运行会在 `artifacts/ai_oneclick/run_YYYYMMDD_HHMMSS/` 生成：

1. `unified/knowledge_base_unified.csv`：AI收集后的候选数据
2. `audit_stage1/ai_review_audit.csv`：首轮审核明细
3. `audit_stage1/knowledge_base_audit_pass.csv`：首轮通过
4. `recheck_stage2/ai_review_recheck.csv`：复检明细
5. `recheck_stage2/knowledge_base_recheck_pass.csv`：复检通过（可入库）
6. `ai_oneclick_report.json`：整轮报告
7. `ai_oneclick_report.md`：摘要

## 5. 质量门与检查

执行整轮后，建议再跑一次门禁：

```powershell
python scripts\validate_ai_pipeline_report.py `
  --report artifacts\ai_oneclick\run_xxx\ai_oneclick_report.json `
  --min-audit-pass-rate 0.25 `
  --min-recheck-pass-rate 0.15 `
  --max-audit-parse-error-rate 0.20
```

若要强制“必须有新增入库”：

```powershell
python scripts\validate_ai_pipeline_report.py `
  --report artifacts\ai_oneclick\run_xxx\ai_oneclick_report.json `
  --require-merge-appended
```

## 6. 现阶段加强建议（全 AI 阶段）

1. 提升数据源质量：优先官方站点、标准正文、可落地 SOP。
2. 提高 recheck 严格度：逐步把 `RecheckMinScore` 从 `82` 调到 `85+`。
3. 强化高风险条目约束：保持 `-StrictHighRisk` 打开。
4. 每周至少一次一键跑批，保证看板和数据持续更新。

## 7. 后期人工接管点（你定的策略）

当数据库稳定后，人工只接管两个点：

1. 发布前抽检：`docs/eval/release_review_log.md`
2. 高风险失败样本复盘：`audit_stage1` 和 `recheck_stage2` 的 blocked 条目

这样人工工作量最小，但仍可保证最终上线质量。

## 8. 故障排查（中转站/API）

如果一键脚本显示“审核全部失败”，先看 `ai_oneclick_report.json` 里的：

1. `call_error_rate`：高于 0.2 通常表示上游 API 异常（如 502/超时/网关错误）
2. `parse_error_rate`：高于 0.2 表示模型输出格式不稳定（非JSON）

建议先执行：

```powershell
python scripts\validate_ai_pipeline_report.py --report <report_json_path>
```

若是 `call_error_rate` 异常，不是数据质量问题，优先检查：

1. `OPENAI_BASE_URL` 是否可访问
2. `OPENAI_API_KEY` 是否有效
3. 中转站是否临时不可用（502/网关错误）
