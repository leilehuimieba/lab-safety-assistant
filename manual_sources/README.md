# 人工补录文件区（Manual Intake）

用于存放“网页抓取失败但可人工获得”的 PDF/Word/PPT 原始文件。

## 目录说明
1. `manual_sources/inbox/`
   - 待处理文件放这里（你上传给我的 PDF 放这里）。
2. `manual_sources/approved/`
   - 人工审核通过、可长期保留的原始文件归档区。
3. `manual_sources/rejected/`
   - 不合格或不再使用的文件归档区。

## 配套清单
1. `data_sources/manual_document_manifest.csv`
   - 人工补录文件元数据（必须填写）。
2. `docs/ops/manual_pdf_intake_workflow.md`
   - 从“放文件”到“入库”的完整流程。

## 最小规则
1. 文件名尽量使用可识别名称（例如：`WS_T_442_2024_临床实验室生物安全指南.pdf`）。
2. 每新增 1 个文件，必须在 `manual_document_manifest.csv` 新增 1 行。
3. 未出现在 manifest 的文件，不进入正式入库流程。

