# PDF / Word / PPT 统一清洗入口

## 目标

这套脚本用于把 `PDF / Word / PowerPoint` 文档统一抽取成项目当前使用的知识库 CSV 格式。

支持的主格式：

- `.pdf`
- `.docx`
- `.pptx`

可选支持的旧格式：

- `.doc`
- `.ppt`

说明：

- `.doc` 和 `.ppt` 需要本机安装 `LibreOffice / soffice` 才能先转换再抽取
- 如果系统里没有 `soffice`，脚本会把旧格式记到跳过报告里，不会静默失败

## 文件位置

脚本：

- `scripts/document_ingest_pipeline.py`

依赖：

- `scripts/requirements-document-ingest.txt`

Manifest 模板：

- `data_sources/document_manifest_template.csv`

输出目录：

- `artifacts/document_ingest/`

## 运行前准备

```powershell
cd D:\workspace\lab-safe-assistant-github
.venv\Scripts\python -m pip install -r scripts\requirements-document-ingest.txt
```

## 最常用的运行方式

### 1. 直接扫 `D:\workspace\data`

项目当前默认输入根目录是 `..\data`，也就是：

- `D:\workspace\data`

直接运行：

```powershell
cd D:\workspace\lab-safe-assistant-github
.venv\Scripts\python scripts\document_ingest_pipeline.py
```

### 2. 连 zip 一起解压再扫

如果资料外层还是压缩包，推荐这样跑：

```powershell
.venv\Scripts\python scripts\document_ingest_pipeline.py --extract-zips
```

### 3. 只跑一小部分做验证

```powershell
.venv\Scripts\python scripts\document_ingest_pipeline.py --limit 5
```

### 4. 跑完后直接并入主知识库

```powershell
.venv\Scripts\python scripts\document_ingest_pipeline.py --extract-zips --merge-into knowledge_base_curated.csv
```

### 5. 控制 PDF 的 OCR fallback 行为

默认会使用：

- `pypdf`
- 必要时回退到 `PyMuPDF / pdfplumber`
- 仍然可疑时再尝试 `RapidOCR`

常用开关：

```powershell
.venv\Scripts\python scripts\document_ingest_pipeline.py --pdf-ocr-mode auto
.venv\Scripts\python scripts\document_ingest_pipeline.py --pdf-ocr-mode off
.venv\Scripts\python scripts\document_ingest_pipeline.py --pdf-ocr-mode always
```

## Manifest 的作用

如果你希望某些文档带上更准确的元数据，比如：

- 来源机构
- 类别
- 子类别
- 风险等级
- 危害类型
- 问题提示词

就把模板复制成：

- `data_sources/document_manifest.csv`

然后按相对路径填写。

模板里的 `path` 相对于输入根目录，例如：

```text
_extracted\安全管理和要求_20260310_110503\工业自动化产品安全要求.pdf
```

## 输出文件

`extract_results.jsonl`

- 每个文档抽取后的基础结果
- 包含文件路径、来源类型、正文预览、字符数等

`clean_documents.jsonl`

- 过滤掉过短或抽取失败的文档后得到的清洗结果

`knowledge_base_documents.csv`

- 与项目现有知识库字段兼容
- 可以直接作为 Dify 的候选导入文件

`run_report.json`

- 记录本次扫描发现多少文件、成功多少、跳过多少

## PDF 清洗增强

当前脚本已经对标准类 PDF 增加了专门的前置页清洗规则，目的是让入库文本尽量从正文开始，而不是把封面、目录、页码一起塞进知识库。

当前已启用的规则：

- 先对 PDF 文本做 `NFKC` 规范化，统一全角数字、全角字母、常见标点
- 自动移除私有区乱码字符、BOM、软连字符等常见脏字符
- 默认先用 `pypdf`，当碎片化明显时自动切换到 `PyMuPDF / pdfplumber`
- 对前缀仍然可疑的小型标准类 PDF，自动补跑 `RapidOCR`
- 如果 OCR 结果更适合修正文档标题，会只用 OCR 修补标题行，避免整篇正文被 OCR 误伤
- 自动识别并跳过标准封面页，例如带“国家标准 / 发布 / 实施”等信号的第一页
- 封面识别会先做紧凑化归一，避免“中 华 人 民 共 和 国 国 家 标 准”这类带空格标题漏判
- 自动识别并跳过“前言 / 引言 / 序言 / 目录 / 目次”等前置页
- 目录页规则只在前置页区域生效，避免误删正文中后段的表格页或附录页
- 自动识别重复出现的短页眉/页脚行，并在清洗阶段移除
- 自动移除单独页码、`Page 1/10` 这类分页噪声
- 自动合并 PDF 抽取时被拆断的短句，减少“每行一小段”的碎片化问题

对于标准类 PDF，脚本会尽量寻找正文起始页，例如：

- `1 范围`
- `1 总则`
- `1 Scope`

一旦识别到正文起始页，起始页之前但又不属于封面/目录的页面，会记为 `front_matter_page` 并跳过。

## extraction_meta 说明

每个 PDF 的抽取结果都会在 `extract_results.jsonl` 中附带 `extraction_meta`，方便做回归检查。当前包含：

- `page_count`: 原始页数
- `kept_page_count`: 清洗后保留页数
- `body_start_page`: 识别到的正文起始页
- `skipped_pages`: 被跳过的页码与原因
- `repeated_line_count`: 被识别为重复页眉/页脚的短行数量
- `pdf_extractor`: 最终采用的 PDF 提取器
- `pdf_candidate_summaries`: 各候选提取器的质量摘要
- `pdf_ocr_title_patched`: 是否用 OCR 修补了标题行

常见 `skipped_pages.reason` 包括：

- `cover_page`
- `toc_page`
- `front_matter_page`
- `empty_page`
- `too_short_after_cleaning`

## 当前策略

- 默认按文档段落分块
- 默认保留适量重叠，降低分块后上下文断裂
- 默认把状态标记为 `draft`
- 默认不会直接覆盖主知识库，除非显式传入 `--merge-into`

## 当前边界

- OCR fallback 已接入，但整本 OCR 仍然比纯文本提取慢很多
- 当前 OCR 使用的是 `RapidOCR`，重点作为兜底和标题修补，不等价于人工校对
- 复杂表格型 Word 文档只做基础文本抽取
- PPT 只抽取页面中的文字，不提取图片里的文字
- 老格式 `.doc/.ppt` 依赖 `LibreOffice`

## 推荐工作流

1. 先把资料放到 `D:\workspace\data`
2. 如果大部分是压缩包，先跑 `--extract-zips`
3. 看 `run_report.json` 和 `clean_documents.jsonl`
4. 用 `document_manifest.csv` 给重要文档补元数据
5. 再跑一遍，确认后使用 `--merge-into knowledge_base_curated.csv`
