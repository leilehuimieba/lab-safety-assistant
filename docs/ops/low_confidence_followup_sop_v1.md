# 低置信度待补任务处理SOP（v1）

## 1. 目标
当“实验室安全小助手”在问答时检索置信度不足，会自动把该问题写入待补任务队列，避免后续优化只靠主观感觉。

该机制用于把“线上真实问题”回流成“数据建设任务”。

## 2. 产物位置
- 队列文件（默认）：`artifacts/low_confidence_followups/data_gap_queue.csv`
- 触发条件（默认）：
1. 未命中任何知识库条目
2. 或最高检索分低于阈值（默认 `3.5`）

可通过环境变量调整：
- `LOW_CONFIDENCE_TOP_SCORE`
- `LOW_CONFIDENCE_QUEUE_FILE`

## 3. 字段说明
`data_gap_queue.csv` 主要字段：
- `created_at`：记录创建时间
- `question_hash`：问题哈希（用于去重）
- `question`：原始提问
- `decision`：分流结果（如 `llm_low_confidence`）
- `low_confidence_reason`：低置信度原因
- `citation_count`：命中文献数量
- `top_score`：最高检索分
- `top_kb_id`：最高命中条目ID
- `suggested_lane`：建议处理泳道（`collect` 或 `clean`）
- `suggested_action`：建议动作
- `status`：任务状态（默认 `todo`）

## 4. 人工处理流程（每周至少一次）
1. 打开 `data_gap_queue.csv`，筛选 `status=todo`。
2. 按优先级处理：
   - `citation_count=0` 优先（通常是“缺数据”）
   - `risk_level=critical/high` 优先（安全影响大）
3. 按 `suggested_lane` 分流：
   - `collect`：补充来源文档，更新 `data_sources/document_manifest.csv`
   - `clean`：修订标签/问句映射/规则，必要时更新 `knowledge_base_curated.csv`
4. 处理完成后将 `status` 改为 `done`，并填写 `notes`（简述改动）
5. 运行质量门：
```powershell
python scripts/quality_gate.py
```
6. 提交PR并关联本周数据任务。

## 5. 验收标准
- 本周新增低置信度记录都有处理去向（`todo` 或 `done`）
- `critical/high` 项不允许长期堆积
- 已处理条目在下一轮问答中不再重复触发

