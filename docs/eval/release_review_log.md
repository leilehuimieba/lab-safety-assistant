# 发布前人工验收记录

说明：

- 每次“知识库批次发布前”必须记录一次人工验收结论。
- 至少两位审核人签名（可填写 GitHub 用户名）。
- 任一高风险错误建议未关闭时，禁止发布。
- 结构化统计请同步查看：`docs/eval/release_review_log.csv`

可选：使用脚本自动追加验收条目

```powershell
python scripts\generate_release_review_entry.py --help
```

脚本会同时写入：

1. `docs/eval/release_review_log.md`（可读版）
2. `docs/eval/release_review_log.csv`（统计版）

门禁开关说明（新增）：

- 首次用 `generate_release_review_entry.py` 追加正式记录后，会自动生成 `docs/eval/release_review_gate_enabled.flag`。
- 一旦该标记文件存在，质量门会强制要求 `release_review_log` 至少存在 1 条正式记录（require-entry）。
- 若你确实要临时回到模板模式，可删除该标记文件（不建议在生产流程中使用）。

模板（复制以下块追加到文末）：

```text
## 发布批次：release-kb-YYYYMMDD

- 审核日期：
- 审核人A：
- 审核人B：
- 使用评测集版本：
- 人工审核题数：
- 通过题数：
- 高风险错误建议（0/1+）：
- 结论（允许发布 yes/no）：
- 备注：
```


## 发布批次：release-kb-20260318-v3

- 审核日期：2026-03-18
- 审核人A：blaze
- 审核人B：codex
- 使用评测集版本：eval_set_v1.csv
- 人工审核题数：10
- 通过题数：0
- 高风险错误建议（0/1+）：0
- 结论（允许发布 yes/no）：no
- 自动统计：
  - document_rows=146
  - web_rows=37
  - merged_rows=183
  - manual_review_total=21
  - manual_review_done=0
  - manual_review_pending=21
- 备注：自动生成：待人工问答审核后再放行

