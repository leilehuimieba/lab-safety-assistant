# KB Cleaning Report

## Summary
- 现有 `knowledge_base_from_pdfs.csv` 共 243 条，来源 21 份 PDF。
- 主题多为设备/检测/标准规范，与“实验室安全问答”目标不匹配。
- 决定：不再使用该 PDF 数据集作为安全助手知识库（保留为归档参考）。

## Evidence
- 主要来源文件包括：无损检测方法、空调规范、设备标准等。
- 检索时容易命中与实验室安全无关内容，导致答复偏离。

## New Curated KB (Draft)
- 生成 `knowledge_base_curated.csv`（25 条核心条目）。
- 覆盖：通风柜、危化品、废液处置、应急处置、PPE、电气安全、生物安全、消防与管理制度。
- 标注 `source_title` 为“待补充”，便于后续替换为真实制度/SOP/应急预案。

## Next Actions
1. 在 Dify 中新建/替换“实验室安全知识库”数据集为 `knowledge_base_curated.csv`。
2. 后续引入真实制度文件后，逐条替换 source 与内容为正式文本。
