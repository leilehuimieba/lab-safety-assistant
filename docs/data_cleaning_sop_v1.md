# 实验室安全小助手 数据清洗SOP v1

## 1. 目标
把采集到的 PDF/Word/PPT/网页 数据，统一清洗为可导入 Dify 的结构化CSV，保证：

- 文本可读（减少乱码）
- 信息可检索（分段合理）
- 来源可追溯（元数据完整）
- 质量可验收（有指标与报告）

## 2. 输入与输出
输入：

- 原始资料目录（建议本机目录，不直接提交大文件到Git）
- `data_sources/document_manifest.csv`
- `data_sources/pdf_special_rules.csv`
- `data_sources/web_seed_urls.csv`

输出：

- `artifacts/<batch_name>/knowledge_base_unified.csv`
- `artifacts/<batch_name>/run_report.json`
- `artifacts/pdf_validation_<name>/manual_review_sheet.csv`

## 3. 清洗前检查（必须）
执行前确认：

- 文档有元数据（manifest中有对应行）
- 文件路径能在当前机器访问
- 重复文件已经去重
- 规则文件字段正确（尤其 `force_ocr`, `body_start_page`, `skip_pages`）

## 4. 标准清洗流程（一步一步）
以下流程建议每周做一次完整批次。

## 4.1 第一步：PDF批量体检（先验收，再入库）
命令模板：

```powershell
python scripts/pdf_batch_validation.py `
  --input-root <YOUR_DATA_ROOT> `
  --output-dir artifacts/pdf_validation_v3 `
  --limit 0 `
  --ocr-review-limit 10 `
  --ocr-review-mode auto `
  --pdf-special-rules data_sources/pdf_special_rules.csv
```

说明：

- `--limit 0` 表示扫描全部匹配PDF
- `--ocr-review-mode auto` 会对疑似乱码PDF做OCR复核
- 输出目录里会生成 `manual_review_sheet.csv`

## 4.2 第二步：人工复核（必须）
处理 `manual_review_sheet.csv`，至少补全这些字段：

- `manual_need_ocr`：yes/no
- `manual_body_start_page_ok`：yes/no
- `manual_skip_pages_ok`：yes/no
- `manual_notes`：异常说明
- `manual_review_status`：done

如果某些PDF稳定异常，写入 `data_sources/pdf_special_rules.csv`：

- `force_ocr=true`
- `body_start_page=<页码>`
- `skip_pages=<页码列表>`

原则：优先做“特例规则”，不要一味增加全局启发式。

## 4.3 第三步：维护manifest（准入名单）
只保留高价值、可追溯、可读性好的文档进入正式批次。建议：

- P0/P1来源优先
- 重复主题保留最佳版本
- 每条都补充 `question_hint`

## 4.4 第四步：跑统一入库流水线
命令模板（推荐）：

```powershell
python scripts/unified_kb_pipeline.py `
  --output-dir artifacts/dify_kb_batch_v3 `
  --document-input-root <YOUR_DATA_ROOT> `
  --document-manifest data_sources/document_manifest.csv `
  --document-only-manifest `
  --document-pdf-special-rules data_sources/pdf_special_rules.csv `
  --pdf-ocr-mode auto `
  --document-max-chars 1800 `
  --document-overlap 100 `
  --web-manifest data_sources/web_seed_urls.csv `
  --web-max-chars 1400 `
  --web-overlap 100
```

如果本批次只做文档，不做网页：

```powershell
python scripts/unified_kb_pipeline.py `
  --output-dir artifacts/dify_kb_batch_v3_docs `
  --document-input-root <YOUR_DATA_ROOT> `
  --document-manifest data_sources/document_manifest.csv `
  --document-only-manifest `
  --document-pdf-special-rules data_sources/pdf_special_rules.csv `
  --pdf-ocr-mode auto `
  --skip-web
```

## 4.5 第五步：质量门与评测
基础门：

```powershell
python scripts/quality_gate.py
pytest
```

问答冒烟评测（调用Dify API）：

```powershell
set DIFY_BASE_URL=<YOUR_DIFY_BASE_URL>
set DIFY_APP_API_KEY=<YOUR_APP_KEY>
python scripts/eval_smoke.py --use-dify --limit 20
```

## 5. 验收指标（建议）
数据清洗批次验收建议值：

- 解析成功率 >= 95%
- 乱码高风险文档占比 <= 5%
- 元数据完整率 >= 98%
- 正式批次中“待人工复核”条目 = 0
- 冒烟评测通过率 >= 80%（MVP阶段）

## 6. 常见问题与处理
问题：PDF乱码严重。  
处理：先启用 `auto` OCR，再对顽固文件加 `pdf_special_rules.csv` 的 `force_ocr=true`。

问题：封面/目录被误当正文。  
处理：在规则里指定 `body_start_page` 和 `skip_pages`，不要手工删原文件。

问题：召回噪声大。  
处理：优先提升manifest质量和question_hint，次优再调 `max_chars/overlap`。

问题：同主题重复答案冲突。  
处理：同主题仅保留“最新且权威”版本，旧版标记下线。

## 7. 分工建议（清洗阶段）
- 清洗负责人：跑流水线、维护规则文件
- 质检同学：人工复核sheet并签字
- 评测同学：跑评测并提交报告
- 负责人：决定是否“发布到Dify正式知识库”

## 8. 发布前检查清单
- `document_manifest.csv` 已完成本批次筛选
- `manual_review_sheet.csv` 已全部处理完成
- `pdf_special_rules.csv` 已加入必要特例
- `knowledge_base_unified.csv` 行数和分类分布正常
- `run_report.json` 无关键报错
- `eval_smoke` 结果达到门槛

