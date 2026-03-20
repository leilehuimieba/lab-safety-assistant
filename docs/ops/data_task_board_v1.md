# 实验室安全小助手 数据任务看板 v1

## 1. 用法
这个看板用于给“找数据同学”和“清洗同学”直接分工。  
建议每周更新2次，PR里同步更新状态。

状态约定：

- `todo`：未开始
- `doing`：进行中
- `review`：待复核
- `done`：已完成
- `blocked`：阻塞

## 2. 周目标（示例）
- 新增高价值资料：30份（P0至少18份）
- 完成清洗入库：500条以上可用chunk
- 关闭人工复核待办：100%
- 完成20题冒烟评测并出报告

## 3. 任务列表模板
| task_id | lane | task_name | owner | status | input | output | deadline | DoD |
|---|---|---|---|---|---|---|---|---|
| T-001 | collect | 收集校内制度（第一批） | 待分配 | todo | 校内公开制度页面/材料 | 10份PDF+manifest记录 | yyyy-mm-dd | 来源可追溯率100% |
| T-002 | collect | 收集实验室SOP（危化品/废液/通风柜） | 待分配 | todo | 学院实验中心资料 | 10份文档+manifest记录 | yyyy-mm-dd | P0类占比>=80% |
| T-003 | collect | 收集常用SDS（乙醇/丙酮/酸碱） | 待分配 | todo | 供应商官方SDS页 | 15份SDS+manifest记录 | yyyy-mm-dd | 文件命名规范率100% |
| T-004 | clean | 运行PDF体检并输出review sheet | 待分配 | todo | 原始资料目录 | `artifacts/pdf_validation_xxx/*` | yyyy-mm-dd | report和sheet生成成功 |
| T-005 | clean | 人工复核sheet并落规则 | 待分配 | todo | `manual_review_sheet.csv` | 更新后的sheet+`pdf_special_rules.csv` | yyyy-mm-dd | pending=0 |
| T-006 | clean | 运行unified入库批次 | 待分配 | todo | manifest+rules+web_seed | `knowledge_base_unified.csv` | yyyy-mm-dd | 解析成功率>=95% |
| T-007 | eval | 运行质量门和冒烟评测 | 待分配 | todo | 批次CSV + Dify API | 评测报告 | yyyy-mm-dd | 通过率>=80% |
| T-008 | release | 发布本周正式批次到Dify | 待分配 | todo | 上述输出物 | 发布记录 | yyyy-mm-dd | 回滚方案可用 |
| T-009 | clean | 处理低置信度待补任务队列 | 待分配 | todo | `artifacts/low_confidence_followups/data_gap_queue.csv` | 更新manifest/KB并关闭todo | yyyy-mm-dd | high/critical 堆积清零 |

## 4. 建议的Git协作规范
分支命名：

- `feat/data-collect-<name>-<date>`
- `feat/data-clean-<name>-<date>`
- `chore/eval-<date>`

提交信息建议：

- `data: add 12 P0 docs and manifest metadata`
- `clean: update pdf rules and regenerate batch v3`
- `eval: smoke test 20 cases, pass 17`

PR最小描述模板：

1. 本次新增了什么
2. 影响了哪些文件
3. 如何验证
4. 风险和回滚方式

## 5. 每周例会最小检查项
- 新增来源是否仍以P0/P1为主
- manifest缺失字段是否清零
- manual review是否有遗留
- 本周回归题（固定10题）是否退化

## 6. 需要人工判断的关键点
- 文档是否属于“可公开共享”范围
- 同主题冲突时哪个版本更权威
- 目录/封面页是否误删正文
- OCR结果是否可靠（抽样读3段）

