# 人工补录 PDF 工作流（放文件 -> 审核 -> 入库）

这个流程解决“网页抓取失败，但你能手工拿到 PDF/附件”的场景。

## 1. 你把文件放哪里
统一放到：

- `manual_sources/inbox/`

示例：

- `manual_sources/inbox/WS_T_442_2024_临床实验室生物安全指南.pdf`
- `manual_sources/inbox/教育部_高校实验室安全检查项目表_2025.pdf`

## 2. 你需要填哪个表
每放 1 个文件，在这里新增 1 行：

- `data_sources/manual_document_manifest.csv`

`path` 字段写相对路径（相对 `manual_sources`），示例：

- `inbox\WS_T_442_2024_临床实验室生物安全指南.pdf`

## 3. 人工审核看什么
最少看 4 项：

1. 文件可打开，正文可读。
2. 来源可信（部委、政府、高校官网附件等）。
3. 内容和实验室安全直接相关。
4. 标题、机构、风险类别等元数据填写合理。

## 4. 一键跑文档入库（仅人工补录文件）
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_manual_pdf_intake.ps1
```

默认会读取：

1. `manual_sources/`（输入目录）
2. `data_sources/manual_document_manifest.csv`（人工补录清单）
3. `data_sources/pdf_special_rules.csv`（PDF 特例规则）

输出目录类似：

- `artifacts/manual_kb_batch_YYYYMMDD_HHMMSS/`

其中关键文件：

1. `knowledge_base_document.csv`
2. `run_report.json`
3. `skipped_files.json`

## 5. 审核通过后怎么入总库
如果这批无明显问题，可以继续跑统一流水线（文档 + 网页）：

```powershell
python scripts/unified_kb_pipeline.py `
  --document-input-root manual_sources `
  --document-manifest data_sources/manual_document_manifest.csv `
  --document-only-manifest `
  --document-pdf-special-rules data_sources/pdf_special_rules.csv `
  --web-manifest data_sources/web_seed_urls_v3_candidates.csv `
  --output-dir artifacts/unified_ingest_manual_v3 `
  --web-fetcher-mode auto `
  --web-skill-script skills/web-content-fetcher/scripts/fetch_web_content.py `
  --web-skill-providers jina,scrapling,direct
```

## 6. 你告诉我之后我会做什么
你只要告诉我：

1. 放了哪些文件名
2. 是否已更新 `manual_document_manifest.csv`

我会接手做：

1. 提取与清洗
2. 结构化编排（分类、风险、问答提示）
3. 人工审核检查点提示
4. 生成可导入知识库的 CSV
