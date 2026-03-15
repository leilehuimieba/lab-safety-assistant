# 网页抓取与正文清洗流水线

## 目标

这套流水线用于把公开网页资料转成当前项目可复用的知识库 CSV，形成最小闭环：

1. 维护待抓取网址清单
2. 自动抓取网页并留存原始 HTML
3. 抽取正文、去噪、分块
4. 产出可导入知识库的 `knowledge_base_web.csv`

## 目录约定

输入清单：

- `data_sources/web_seed_urls.csv`

运行脚本：

- `scripts/web_ingest_pipeline.py`

依赖清单：

- `scripts/requirements-web-ingest.txt`

输出目录：

- `artifacts/web_ingest/`

主要输出文件：

- `fetch_results.jsonl`
- `clean_documents.jsonl`
- `knowledge_base_web.csv`
- `run_report.json`

## 清单字段

`data_sources/web_seed_urls.csv` 当前包含以下字段：

- `source_id`
- `title`
- `source_org`
- `category`
- `subcategory`
- `lab_type`
- `risk_level`
- `hazard_types`
- `url`
- `tags`
- `language`
- `question_hint`

建议优先加入公开、权威、结构清晰的来源，例如：

- 高校实验室安全制度页
- 实验室 SOP 页面
- 危化品管理制度页
- 学院或实验中心公开的安全规范页

## 运行方式

先在项目根目录创建虚拟环境并安装依赖：

```powershell
cd D:\workspace\lab-safe-assistant-github
py -m venv .venv
.venv\Scripts\python -m pip install -r scripts\requirements-web-ingest.txt
```

执行默认流水线：

```powershell
.venv\Scripts\python scripts\web_ingest_pipeline.py
```

自定义输出目录：

```powershell
.venv\Scripts\python scripts\web_ingest_pipeline.py --output-dir artifacts\web_ingest_demo
```

调大并发或调整分块大小：

```powershell
.venv\Scripts\python scripts\web_ingest_pipeline.py --concurrency 5 --max-chars 1500 --overlap 150
```

确认结果没有问题后，直接并入现有知识库：

```powershell
.venv\Scripts\python scripts\web_ingest_pipeline.py --output-dir artifacts\web_ingest_demo --merge-into knowledge_base_curated.csv
```

## 输出解释

`fetch_results.jsonl`

- 记录每个 URL 的抓取状态、最终 URL、状态码、原始 HTML 存放位置

`clean_documents.jsonl`

- 记录正文提取后的文档内容、摘要、发布日期、来源机构等信息

`knowledge_base_web.csv`

- 与项目现有知识库字段兼容
- 可以作为 Dify 知识库的新增候选数据
- 默认状态为 `draft`

`--merge-into`

- 会按 `id` 去重后，把新增网页条目写入现有知识库 CSV
- 适合“先跑一批网页资料，再并入主库”的工作流

`run_report.json`

- 用于快速查看这次跑批抓取了多少页、成功多少页、导出了多少条知识片段

## 当前边界

- 只抓取公开网页，不处理登录态页面
- 只做规则清洗，不做 LLM 改写
- 适合“制度页、通知页、规范页、SOP 页”这类结构较清晰的文本网页
- 对 PDF、图片扫描件、复杂 JS 动态页，后续需要单独补采集器

## 建议工作流

1. 先把 10 到 20 个权威网址补进 `web_seed_urls.csv`
2. 跑一遍流水线，观察 `clean_documents.jsonl`
3. 人工筛掉噪声页、导航页、重复页
4. 复核 `knowledge_base_web.csv` 中的重要条目
5. 再导入 Dify 或并入人工整理的 `knowledge_base_curated.csv`

## 下一步建议

后续如果继续增强，优先级建议是：

1. 增加 PDF 抽取与网页抽取统一入口
2. 增加正文质量评分和重复内容去重
3. 增加“自动摘要改写成问答条目”的 LLM 增强步骤
