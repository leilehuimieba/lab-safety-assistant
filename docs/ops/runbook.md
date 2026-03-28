# 实验室安全小助手运行手册

## 文档目的

本手册用于说明如何基于本仓库现有材料，复现“实验室安全小助手”的最小可运行原型，并完成知识库导入、工作流配置、基础测试和演示准备。

本手册面向以下读者：

- 项目组成员
- 指导老师或评审中需要了解复现路径的人
- 后续接手维护该项目的同学

## 当前仓库定位

本仓库是“项目核心成果仓库”，而不是完整运行环境镜像。仓库中保留了以下可公开材料：

- 项目申报书
- 核心知识库样例
- 规则库
- 评测集和验收指标
- 检索调参记录

本仓库不包含以下内容：

- Dify 运行数据卷
- 本地数据库和上传文件
- API 密钥和私有配置
- Docker volumes
- 临时调试日志

因此，复现流程需要先在本地准备 Dify 运行环境，再将本仓库中的资料导入进去。

## 目标复现结果

完成本手册后，应至少达到以下状态：

- Dify 应用可打开并正常对话
- 已导入实验室安全知识库
- 工作流包含“开始 -> 知识检索 -> LLM -> 回答”主链路
- 可正确回答通风柜、危化品、触电、火灾等典型问题
- 可使用评测集进行抽样验证

## 前置条件

### 软件环境

- Windows、macOS 或 Linux 均可
- Docker Desktop 或等效 Docker 环境
- Git
- 浏览器

### 服务环境

- 已准备可用的 Dify 自部署环境
- 已有一个可用的大模型提供方
- 如果后续要做高质量检索，建议额外准备 Embedding 服务

### 项目材料

建议从本仓库使用以下文件：

- `knowledge_base_curated.csv`
- `safety_rules.yaml`
- `eval_set_v1.csv`
- `eval_criteria.md`
- `retrieval_tuning_report.md`

## 第一步：启动 Dify

### 方式一：使用已有本地 Dify 环境

如果本地已经部署过 Dify，直接确认以下内容：

- Web 页面可访问
- 管理后台可登录
- 当前工作区可正常创建应用和知识库

### 方式二：新建一套 Dify 环境

如果需要重新部署，可以参考 Dify 官方自部署方案。最低要求是：

- `web`
- `api`
- `worker`
- 数据库
- 向量或检索相关组件

建议将运行环境和本仓库分离，避免把运行数据直接提交到 Git 仓库中。

## 第二步：导入知识库

### 知识库文件

当前推荐导入文件：

- `knowledge_base_curated.csv`

这个文件是经过清洗后的核心知识库样例，覆盖了化学、电气、通用应急等基础场景。

### 导入建议

- 新建知识库：`实验室安全知识库`
- 优先导入清洗后的 `knowledge_base_curated.csv`
- 不建议直接导入未清洗的大体积原始资料
- 如果旧版知识库已经存在，建议先归档旧文档，再导入新文件

### 当前推荐配置

- 分段模式：`automatic`（或平台默认推荐）
- 索引模式：优先 `high_quality`
- 检索模式：混合检索（向量 + 关键词）
- Top K：`5`
- Score threshold：`0.5`（可在 `0.45~0.55` 小范围微调）

## 第三步：创建应用

### 应用类型

建议使用：

- `Advanced Chat`

这样便于配置工作流、知识检索和回答节点。

### 应用命名建议

- `实验室安全小助手`

### 应用目标

用户输入实验室安全相关问题，系统通过知识检索和规则约束返回结构化、安全边界明确的回答。

## 第四步：配置工作流

### 最小主链路

当前最小可用工作流建议为：

1. `Start`
2. `Knowledge Retrieval`
3. `LLM`
4. `Answer`

### 关键点 1：知识检索节点

建议配置：

- 检索模式：多路检索或默认知识检索模式
- `Top K = 5`
- 暂不启用重排序模型（当前可先关闭，后续按评测结果决定）

当前建议优先保证混合检索稳定，再考虑引入 rerank。

### 关键点 2：LLM 节点

LLM 节点负责：

- 结合检索内容生成实验室安全回答
- 保持语言清晰、步骤明确
- 避免对危险行为给出鼓励性回答

### 关键点 3：Answer 节点绑定

必须确认 `Answer` 节点输出的是 LLM 实际生成文本，而不是错误绑定到中间变量。

当前原则：

- `Answer` 节点应直接引用 LLM 的 `text` 输出

如果出现“回答节点输出为空”或“输出不是模型文本”的问题，优先检查变量绑定是否正确。

## 第五步：规则库使用建议

本仓库中的 `safety_rules.yaml` 用于沉淀高风险场景处理规则，建议使用方式如下：

- 用于设计系统提示词和规则提示
- 用于梳理危险问题的约束逻辑
- 用于统一应急场景回答结构

当前规则库重点覆盖：

- 酸液飞溅
- 火灾
- 气体泄漏
- 吸入或误食
- 灼伤
- 割伤
- 其他高风险危险操作

## 第六步：基础验证

### 推荐测试问题

建议先手工测试以下问题：

1. 通风柜什么时候必须开启？
2. 乙醇应如何储存？
3. 盐酸和漂白水能混吗？
4. 有人触电了怎么办？
5. 实验室着火怎么办？

### 预期验证点

- 是否能命中正确知识条目
- 是否能给出场景化回答
- 是否能识别危险行为并进行约束
- 是否能在应急场景下给出优先级明确的处理步骤

## 第七步：使用评测集

### 评测文件

- `eval_set_v1.csv`
- `eval_criteria.md`

### 使用方法

- 从评测集中抽取 5 到 10 条问题进行首轮测试
- 记录回答是否命中关键要点
- 对照 `eval_criteria.md` 判断是否达到 MVP 要求

### 建议先看三类问题

- 常规问答类
- 危险行为纠偏类
- 应急处理类

## 第八步：演示准备

建议配套使用：

- `docs/ops/demo_script.md`

演示前建议确认：

- Dify 页面打开正常
- 典型问题已联调通过
- 浏览器缓存和登录状态稳定
- 现场网络可用

## 当前已知限制

### 1. 正式数据源还不完整

当前知识库属于“核心样例集”，更适合做 MVP 演示和结构验证。若要提升可信度，需要继续接入正式制度文件、SOP 和 MSDS。

### 2. Embedding / 混合检索依赖本地服务稳定性

当前方案可使用 Ollama + bge-m3 实现混合检索；若本地服务不可用，会退化为关键词召回并带来噪声。

### 3. 回答准确率仍依赖知识条目密度

实验室安全问题覆盖面广，当前版本已覆盖核心场景，但还需要继续扩展条目数量和来源质量。

## 常见问题排查

### 问题 1：知识库已导入，但回答很空泛

排查方向：

- 检查知识库文件是否导入的是清洗后版本
- 检查是否命中了正确知识条目
- 检查 LLM 提示词是否过于泛化

### 问题 2：回答节点没有输出 LLM 文本

排查方向：

- 检查 `Answer` 节点变量绑定
- 确认引用的是 LLM 节点的 `text` 字段

### 问题 3：高风险问题回答不够明确

排查方向：

- 补充 `safety_rules.yaml` 中的规则
- 强化系统提示词中的拒答和纠偏逻辑
- 增加应急场景知识条目

### 问题 4：召回结果噪声较多

排查方向：

- 继续扩展知识条目的关键词和同义表达
- 引入 Embedding 和混合检索
- 在可行时引入 rerank 模型

## 第九步：提交前质量门（推荐）

建议在每次提交前执行：

```powershell
python scripts/quality_gate.py
```

可选启用 pre-commit：

```powershell
pip install pre-commit
pre-commit install
```

最小单测：

```powershell
pytest
```

自动化冒烟评测（10 条快速回归）：

```powershell
set DIFY_BASE_URL=http://localhost
set DIFY_APP_API_KEY=<app-xxxx>
python scripts/eval_smoke.py --use-dify --limit 10
```

人工复核流程：

```powershell
# 1) 先得到 eval_smoke 产出的 detailed_results.csv
python scripts/eval_review.py --detailed-results <detailed_results.csv> --generate-template

# 2) 人工填写模板后，生成最终汇总
python scripts/eval_review.py --detailed-results <detailed_results.csv> --manual-review-csv <manual_review_filled.csv>
```

评测看板与周趋势（自动汇总）：

```powershell
python scripts/generate_eval_dashboard.py --repo-root .
```

生成产物：

- `docs/eval/eval_dashboard.md`
- `docs/eval/eval_dashboard_data.json`
- `docs/eval/eval_dashboard_runs.csv`

真实回归流水线（自动 smoke + 自动复核汇总 + 刷新看板）：

```powershell
set DIFY_BASE_URL=http://localhost
set DIFY_APP_API_KEY=<app-xxxx>
python scripts/run_eval_regression_pipeline.py --repo-root . --update-dashboard --dify-timeout 30 --eval-concurrency 4
```

说明：
- 默认会先调用 `GET /v1/parameters` 做连通性预检，失败会提前退出，避免整轮长时间等待。
- 如需临时跳过预检，可加 `--skip-preflight`（仅建议排障时使用）。
- 可开启“主通道超时后自动降级到备用通道”：设置 `DIFY_FALLBACK_BASE_URL`、`DIFY_FALLBACK_APP_API_KEY`，并加 `--retry-on-timeout 1`。

模型通道 A/B 对比（自动切模型、自动恢复配置）：

```powershell
python scripts/run_model_ab_eval.py `
  --repo-root . `
  --app-id <your_app_id> `
  --dify-base-url http://localhost:8080 `
  --model-a MiniMax-M2.5 `
  --model-b gpt-5.2-codex `
  --limit 6 `
  --dify-timeout 30 `
  --eval-concurrency 4
```

默认会自动输出“失败分簇 + Top10 修复清单”：

- `eval_failure_clusters.csv`
- `eval_failure_clusters.md`
- `eval_top10_fix_list.csv`

如果只想跑基础回归，可加：

```powershell
python scripts/run_eval_regression_pipeline.py --repo-root . --skip-failure-analysis
```

门禁规则（已启用）：

- 标记文件：`docs/eval/eval_dashboard_gate_enabled.flag`
- 检查脚本：`scripts/validate_eval_dashboard_gate.py`
- 触发条件：关键指标连续两周低于阈值时，`quality_gate` 失败并阻止发布。

## 第十步：使用网页提取 Skill（可选）

当需要从链接提取正文并做实验入库时，可使用仓库内置 Skill：

```powershell
python skills/web-content-fetcher/scripts/fetch_web_content.py `
  --url "https://example.com/post" `
  --max-chars 30000 `
  --pretty
```

批量模式（从 `web_seed_urls.csv` 读取）：

```powershell
python skills/web-content-fetcher/scripts/fetch_web_content.py `
  --url-file data_sources/web_seed_urls.csv `
  --url-column url `
  --out-json artifacts/web_fetch_output.json
```

合规要求请先阅读：

- `docs/ops/web_content_fetch_skill_合规说明_v1.md`
- `skills/web-content-fetcher/references/compliance_scope.md`

## 后续建议

在完成本手册的最小复现后，建议继续推进：

- 正式数据源建设
- 规则库扩充
- Embedding 与混合检索接入
- 答辩演示脚本完善
- 更系统的评测记录与版本对比

## 相关文档

- `docs/ops/demo_script.md`
- `docs/pipeline/data_source_plan.md`
- `eval_set_v1.csv`
- `eval_criteria.md`
- `retrieval_tuning_report.md`

