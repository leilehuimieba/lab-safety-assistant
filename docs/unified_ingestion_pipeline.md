# 统一知识库入库入口

## 目标

把这几个来源统一沉淀为同一套知识库 CSV：

- PDF
- Word
- PPT
- 网页

统一入口脚本：

- `scripts/unified_kb_pipeline.py`

统一输出文件：

- `artifacts/unified_ingest/knowledge_base_unified.csv`

这份 CSV 与现有知识库字段兼容，可以继续并入 Dify 使用的候选知识库。

## 运行方式

### 1. 文档 + 网页一起跑

```powershell
cd D:\workspace\lab-safe-assistant-github
.venv\Scripts\python scripts\unified_kb_pipeline.py
```

### 2. 指定文档目录

```powershell
.venv\Scripts\python scripts\unified_kb_pipeline.py --document-input-root D:\workspace\data\_extracted
```

### 3. 控制 PDF OCR fallback

```powershell
.venv\Scripts\python scripts\unified_kb_pipeline.py --pdf-ocr-mode auto
.venv\Scripts\python scripts\unified_kb_pipeline.py --pdf-ocr-mode off
.venv\Scripts\python scripts\unified_kb_pipeline.py --pdf-ocr-mode always
```

### 4. 只验证部分文档

```powershell
.venv\Scripts\python scripts\unified_kb_pipeline.py --document-limit 3
```

### 5. 跳过网页或跳过文档

```powershell
.venv\Scripts\python scripts\unified_kb_pipeline.py --skip-web
.venv\Scripts\python scripts\unified_kb_pipeline.py --skip-documents
```

### 6. 跑完直接并入已有知识库

```powershell
.venv\Scripts\python scripts\unified_kb_pipeline.py --merge-into knowledge_base_curated.csv
```

## 输出结构

- `artifacts/unified_ingest/documents/`
  - 文档子流程的中间产物
- `artifacts/unified_ingest/web/`
  - 网页子流程的中间产物
- `artifacts/unified_ingest/knowledge_base_unified.csv`
  - 最终合并后的统一 CSV
- `artifacts/unified_ingest/run_report.json`
  - 统一入口的汇总报告

## 已验证样例

当前已经完成一轮烟雾验证：

- 输出目录：`artifacts/unified_ingest_v2/`
- 文档样本：`3` 份
- 网页样本：`2` 页成功入库
- 合并结果：`76` 行统一知识库记录

## 配套验收脚本

如果要先做 PDF 质量抽检，再决定是否批量入库，可以使用：

- `scripts/pdf_batch_validation.py`

示例：

```powershell
.venv\Scripts\python scripts\pdf_batch_validation.py --input-root D:\workspace\data --limit 10
.venv\Scripts\python scripts\pdf_batch_validation.py --input-root D:\workspace\data --limit 10 --ocr-review-mode auto
```

说明：

- 第一轮基线抽检固定使用 `ocr=off`，先拿到纯文本提取质量
- 第二轮只对高风险样本做 OCR 复核，默认 `--ocr-review-mode always`
- `--pdf-ocr-mode` 仍可继续使用，但现在只是 `--ocr-review-mode` 的兼容别名

输出：

- `artifacts/pdf_validation_batch_10/validation_report.csv`
- `artifacts/pdf_validation_batch_10/validation_report.md`
- `artifacts/pdf_validation_batch_10/validation_report.json`

报告会记录：

- `body_start_page`
- `skipped_pages`
- `pdf_extractor`
- `garbled_score`
- `garbled_level`
- `ocr_candidate_present`
- `ocr_reviewed`
- `title_patched`

## 推荐顺序

1. 先跑 `pdf_batch_validation.py` 看 10 份抽检结果
2. 根据抽检结果调整 `document_manifest.csv`
3. 再跑 `unified_kb_pipeline.py`
4. 最后把 `knowledge_base_unified.csv` 并入主知识库
