# PDF 人工核验标准 v1

## 1. 目的
本标准用于规范 PDF 批量体检后的人工复核，确保入库内容可读、可检索、可追溯。

适用文件：

- `artifacts/<batch>/manual_review_sheet.csv`
- `artifacts/<batch>/validation_report.json`

## 2. 什么时候必须人工核验
以下任一情况触发人工核验：

- 乱码分数高（garbled_score 高于阈值）
- 自动判断可能需要 OCR
- 标题异常或正文为空
- 封面/目录识别不稳定
- 文档属于高优先级来源（P0/P1）

## 3. 人工核验核心字段（必须填）
在 `manual_review_sheet.csv` 中至少填这些字段：

- `manual_need_ocr`：`yes/no`
- `manual_body_start_page_ok`：`yes/no`
- `manual_skip_pages_ok`：`yes/no`
- `manual_notes`：简短说明问题与处理
- `manual_review_status`：`done`

## 4. 具体判定规则
## 4.1 是否需要 OCR（manual_need_ocr）
判为 `yes` 的条件：

- 连续两段以上出现明显乱码（无法阅读）
- 专有名词大量错字或丢字
- 提取文本严重断裂，无法形成完整句子

判为 `no` 的条件：

- 偶发个别错字，但不影响理解
- 正文信息完整、语义可读

## 4.2 正文起始页是否正确（manual_body_start_page_ok）
判为 `yes` 的条件：

- 起始页打开后就是正文条款/步骤/要求
- 之前页为封面、版权页、目录页

判为 `no` 的条件：

- 起始页仍是目录或附录封面
- 起始页跳过过多，导致正文丢失

## 4.3 跳过页是否合理（manual_skip_pages_ok）
判为 `yes` 的条件：

- 跳过页主要是封面、目录、空白页、广告页
- 未误删正文关键内容

判为 `no` 的条件：

- 被跳过页面包含关键条款或操作步骤

## 5. 异常文档处理优先级
处理顺序建议：

1. 先修高风险场景文档（危化品、应急、电气、气瓶）
2. 再修高频问答文档
3. 最后修低频扩展文档

## 6. 规则回写（关键）
若某PDF多次出现同类问题，不要每次人工修，直接写入：

- `data_sources/pdf_special_rules.csv`

常用字段：

- `force_ocr=true`
- `body_start_page=<页码>`
- `skip_pages=<页码列表>`
- `notes=<原因>`

## 7. 通过门槛（建议）
每个批次建议达到：

- 待人工项清零：`manual_review_status=done`
- 乱码高风险比例 <= 5%
- `body_start_page` 误判率 <= 10%
- 封面/目录误删率 <= 5%

## 8. 复核同学注意事项
- 只修“提取规则和标注”，不修改原始PDF内容
- 一次只改一类问题，便于回溯
- 每次批处理后都留存报告目录，禁止覆盖历史结果

