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
python scripts/run_eval_regression_pipeline.py --repo-root . --update-dashboard --dify-response-mode streaming --dify-timeout 60 --eval-concurrency 1
```

说明：
- 默认会先调用 `GET /v1/parameters` 做连通性预检，失败会提前退出，避免整轮长时间等待。
- 默认还会做一次 `POST /v1/chat-messages` 的快速预检（`blocking` 模式），用于提前识别模型或检索链路异常。
- 如需临时跳过预检，可加 `--skip-preflight`（仅建议排障时使用）。
- 如需临时跳过 chat 预检，可加 `--skip-chat-preflight`（仅建议排障时使用）。
- 可开启“主通道超时后自动降级到备用通道”：设置 `DIFY_FALLBACK_BASE_URL`、`DIFY_FALLBACK_APP_API_KEY`，并加 `--retry-on-timeout 1`。
- 若报错包含 `host.docker.internal:11434 unreachable`，通常是嵌入模型通道不可达。优先检查 `docker-worker-1` 日志，并修复 embedding 配置后再重跑。
- 可参考专项排障记录：`docs/ops/live_regression_blocker_20260328.md`

附加参数（2026-03 更新）：
- `--dify-response-mode blocking|streaming`：评测链路调用 Dify 的响应模式，默认 `streaming`（当前环境下更稳定）。
- `--skip-chat-preflight`：仅跳过 chat 预检，保留 `/parameters` 预检。

工作流应急脚本（可回滚）：
- `python scripts/patch_workflow_retrieval.py --workflow-id <id> --mode disable-retrieval`
- `python scripts/patch_workflow_retrieval.py --workflow-id <id> --mode restore --backup-file <path>`
- `python scripts/patch_workflow_model.py --workflow-id <id> --model-name gpt-5.2-codex`

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

模型不可用自动回退（高优先级推荐）：

先做运行前健康体检（推荐每次都执行）：

```powershell
set DIFY_BASE_URL=http://localhost:8080
set DIFY_APP_API_KEY=<app-xxxx>
python scripts/check_live_eval_health.py `
  --repo-root . `
  --dify-base-url %DIFY_BASE_URL% `
  --dify-app-key %DIFY_APP_API_KEY% `
  --response-mode streaming `
  --embedding-containers docker-api-1 docker-worker-1 docker-plugin_daemon-1
```

若体检失败，先修复 embedding 映射后再继续：

```powershell
python scripts/fix_embedding_host_mapping.py --embed-container fake-ollama --containers docker-api-1 docker-worker-1 docker-plugin_daemon-1
```

体检通过后执行自动回退回归：

```powershell
set DIFY_BASE_URL=http://localhost:8080
set DIFY_APP_API_KEY=<app-xxxx>
python scripts/run_eval_with_model_failover.py `
  --repo-root . `
  --workflow-id <workflow_id> `
  --primary-model gpt-5.2-codex `
  --fallback-model MiniMax-M2.5 `
  --health-allow-chat-timeout-pass `
  --canary-limit 3 `
  --canary-timeout 20 `
  --canary-retry-on-timeout 0 `
  --canary-timeout-failover-threshold 1.0 `
  --limit 20 `
  --dify-timeout 60 `
  --eval-concurrency 1 `
  --timeout-failover-threshold 1.0 `
  --retry-on-timeout 1 `
  --update-dashboard
```

说明：
- 默认会先调用 `check_live_eval_health.py`；若体检失败会提前退出，避免整轮长时间等待后才失败。
- 可用 `--skip-health-check` 临时跳过体检（仅建议排障时使用）。
- 若环境存在“chat preflight 偶发超时”，可加 `--health-allow-chat-timeout-pass`：允许先进入 canary，由真实样本决定是否继续全量。
- 默认启用 Canary（`--canary-limit` + `--canary-timeout`）：先跑小样本短超时回归；若超时比率达到阈值，会快速触发回退或直接中止，避免全量无效等待。
- Canary 默认建议 `--canary-retry-on-timeout 0`，用于故障场景快速止损；全量阶段再按 `--retry-on-timeout` 使用常规重试策略。
- 若要直接跑全量，可加 `--skip-canary`。
- 为减少重复探测和抖动，外层健康检查通过后，内层回归默认跳过重复 preflight；若你关闭健康检查（`--skip-health-check`），内层会恢复 preflight。
- 先用主模型跑真实回归；若检测到 `model_not_found`、`InvokeServerUnavailableError`、`503` 等模型不可用特征，会自动切到备用模型再跑一轮。
- 若主模型“返回码成功但超时占比过高”，也可按阈值触发回退（`--timeout-failover-threshold`，默认 `1.0` 表示全超时才触发）。
- 自动输出报告到 `artifacts/model_failover_eval/run_*/model_failover_report.json`（含触发原因、主备运行目录、错误摘要）。
- 默认保留最终可用模型作为在线模型；如需跑完后恢复主模型，加 `--restore-primary-after-run`。
- 安全策略：脚本执行中若出现异常中断，会自动回切到主模型，避免工作流停留在未验证通过的回退模型。

将 failover 结果同步到看板/门禁（推荐）：

```powershell
python scripts/generate_failover_status.py --repo-root . --days 7
```

产物：
- `docs/eval/failover_status.json`
- `docs/eval/failover_status.md`

门禁可选启用 failover 状态强校验：

```powershell
python scripts/validate_eval_dashboard_gate.py `
  --repo-root . `
  --enforce-failover-status `
  --failover-max-age-hours 72 `
  --failover-fail-streak-threshold 2
```

一键串联（健康检查 -> 回归/回退 -> failover快照 -> 风险说明 -> 门禁）：

```powershell
set DIFY_BASE_URL=http://localhost:8080
set DIFY_APP_API_KEY=<app-xxxx>
python scripts/run_eval_release_oneclick.py `
  --repo-root . `
  --workflow-id <workflow_id> `
  --primary-model gpt-5.2-codex `
  --fallback-model MiniMax-M2.5 `
  --health-allow-chat-timeout-pass `
  --canary-limit 3 `
  --canary-timeout 20 `
  --canary-retry-on-timeout 0 `
  --limit 20 `
  --dify-timeout 60 `
  --eval-concurrency 1 `
  --retry-on-timeout 1 `
  --failover-fail-streak-threshold 2
```

Windows 封装脚本（等价执行）：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_eval_release_oneclick.ps1 `
  -RepoRoot . `
  -WorkflowId <workflow_id> `
  -PrimaryModel gpt-5.2-codex `
  -FallbackModel MiniMax-M2.5 `
  -FailoverFailStreakThreshold 2
```

退出码说明：

- `0`：全链路成功，门禁通过。
- `2`：流程执行完成但被门禁阻断（需要修复后重跑）。
- `1`：链路中间步骤失败（环境/脚本/接口异常）。
- 默认会在门禁后继续执行 `validate_release_policy.py`（`demo` profile）。
- 可通过 `--release-policy-profile prod` 切换到更严格发布策略。
- 可通过 `--release-policy-run-secondary --release-policy-secondary-profile prod` 同时产出 `demo+prod` 双轨结论。
- 若希望 secondary（如 `prod`）失败时也阻断，可加 `--release-policy-enforce-secondary`。
- 临时跳过该步骤可用 `--skip-release-policy-check`（不建议常态化使用）。

failover 门禁判定（分级策略）：

- `latest=pass`：正常通过。
- `latest=degraded`：默认记预警（`warning`），不直接阻断；如需静默该预警，可加 `--failover-allow-degraded`。
- `latest=fail`：仅当最近连续 `fail` 次数达到 `--failover-fail-streak-threshold` 才阻断发布；未达到阈值时仅预警。

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
- 触发条件（新版）：
- 先看链路健康（`route_success_rate`、`route_timeout_rate`）连续两周是否达标；
- 链路健康达标后，才对质量指标（拒答/应急/常规/覆盖）做连续周门禁；
- 这样可避免“上游超时导致质量门误判”。

临时豁免（仅限短窗口）：

- 配置文件：`docs/eval/eval_dashboard_gate_override.json`
- 示例模板：`docs/eval/eval_dashboard_gate_override.example.json`
- 推荐模式：`warn_only`（保留告警、允许临时放行）
- 建议填写：`reason`、`ticket`、`approver`，并设置 `starts_on`/`ends_on`

自动发布风险说明：

```powershell
python scripts/generate_release_risk_note.py --repo-root .
```

- 输出：`docs/eval/release_risk_note_auto.md`
- 明细：`docs/eval/release_risk_note_auto.json`
- 当执行 `run_eval_regression_pipeline.py --update-dashboard` 时，会自动生成这两份文件（可加 `--skip-risk-note` 跳过）

发布前策略门槛（V5，可执行）：

```powershell
python scripts/validate_release_policy.py `
  --repo-root . `
  --profile demo `
  --strict
```

说明：

- 策略文件：`docs/eval/release_policy_v5.json`
- 支持 profile：`demo`、`prod`
- `prod` 关键质量阈值（硬门禁）：`emergency_pass_rate >= 0.90`、`coverage_rate >= 0.85`、`qa_pass_rate >= 0.85`
- `demo` 关键质量阈值（演示门槛）：`emergency_pass_rate >= 0.80`、`coverage_rate >= 0.75`
- 输出：
- `docs/eval/release_policy_check_demo.json/.md`
- `docs/eval/release_policy_check_prod.json/.md`
- 返回码：
- `0` 表示通过策略校验
- `1` 表示被策略阻断

生成发布就绪看板与阻断原因 TopN：

```powershell
python scripts/generate_release_readiness_dashboard.py `
  --repo-root . `
  --profiles demo,prod `
  --strict-profiles demo,prod
```

- 输出：
- `docs/eval/release_readiness_dashboard.json/.md`
- `docs/eval/release_blocker_topn.csv/.md`
- `docs/ops/release_fix_plan_auto.csv/.md`
- 该流程会按 `blocking_reason` 尝试保留已存在的 `owner/status/eta`，避免覆盖人工分配。

上线前一键预检（新增，建议作为最终发布前最后一步）：

```powershell
python scripts/release/go_live_preflight.py `
  --repo-root . `
  --release-dir release_exports/v8.1 `
  --web-health-url http://127.0.0.1:8088/health
```

PowerShell 封装（Windows 推荐）：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_go_live_preflight.ps1 `
  -RepoRoot . `
  -ReleaseDir release_exports/v8.1 `
  -WebHealthUrl http://127.0.0.1:8088/health
```

- 输出：
- `docs/ops/go_live_readiness.json`
- `docs/ops/go_live_readiness.md`
- 返回码：
- `0`：PASS（可上线）
- `2`：BLOCK（禁止上线）
- `3`：WARN（有告警，默认也阻断；可加 `--allow-warning-pass` 放行）

GitHub 手动预检工作流：

- `.github/workflows/go-live-preflight.yml`
- 支持在 Actions 页面指定 `release_dir`，并可按需跳过 web health（CI 场景常用）。

发布稳定性验收（连续多轮）：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_release_stability_check.ps1 `
  -RepoRoot . `
  -Rounds 3 `
  -IntervalSec 30 `
  -WorkflowId <workflow_id> `
  -DifyBaseUrl http://localhost:8080 `
  -DifyAppKey <app_key> `
  -SkipHealthCheck `
  -SkipCanary
```

- 输出：
- `docs/eval/release_stability_check.json/.md`
- `artifacts/release_stability_check/run_*/`
- 返回码：
- `0`：稳定性验收通过（全部轮次 PASS）
- `2`：稳定性验收失败（至少一轮 BLOCK/FAIL）

GitHub 手动稳定性工作流：

- `.github/workflows/release-stability-check.yml`
- 默认 `skip_failover_eval=true`（适合 CI 做“策略层稳定性”）
- 若要做真实链路稳定性，请在自有 runner/服务器执行本地脚本。

生成低置信队列看板（建议与发布看板同时刷新）：

```powershell
python scripts/generate_low_confidence_dashboard.py --repo-root .
```

- 输出：
- `docs/eval/low_confidence_dashboard.json/.md`
- 输入队列默认：`artifacts/low_confidence_followups/data_gap_queue.csv`

发布策略 schema 校验（建议提交前执行）：

```powershell
python scripts/validate_release_policy_schema.py --repo-root .
```

修复计划质量门（建议提交前执行）：

```powershell
python scripts/validate_release_fix_plan.py --repo-root .
```

将 P0 修复任务同步到 GitHub Issues（建议在发布前执行）：

```powershell
# 实际执行（需要 GITHUB_TOKEN + GITHUB_REPOSITORY）
python scripts/sync_release_fix_plan_issues.py --repo-root . --only-priority P0 --assign-from-owner

# 预演模式（不写入 GitHub）
python scripts/sync_release_fix_plan_issues.py --repo-root . --only-priority P0 --assign-from-owner --dry-run
```

- 输入：`docs/ops/release_fix_plan_auto.csv`
- 输出：
- `docs/ops/release_fix_plan_sync_report.json`
- `docs/ops/release_fix_plan_sync_report.md`
- 降级策略：
- 若 `owner` 字段包含非法用户名，自动跳过非法 token 并记录 warning
- 若 assignee 无法绑定（非协作者/不存在），自动降级为“创建 issue 但不指派”，并记录 warning
- 同步规则：
- `status in [todo,in_progress,blocked]`：创建或更新 issue
- `status in [done,wont_fix]`：关闭已关联 issue
- `task_id` 通过 `<!-- RELEASE_FIX_TASK:{task_id} -->` 标记实现可追踪绑定

逾期升级（P0）：

```powershell
# 实际执行（每日监控工作流会自动跑）
python scripts/escalate_release_fix_overdue.py --repo-root . --priority P0

# 预演模式
python scripts/escalate_release_fix_overdue.py --repo-root . --priority P0 --dry-run
```

- 输出：
- `docs/ops/release_fix_overdue_report.json`
- `docs/ops/release_fix_overdue_report.md`
- 升级动作：
- 给逾期任务 issue 自动打 `release-fix-overdue`
- 逾期天数达到阈值（默认 3 天）自动升级 `p1-release-fix`
- 每日最多一条提醒评论（按 `RELEASE_FIX_OVERDUE:{task_id}:{date}` 去重）

GitHub 自动监控（每日）：

- 工作流：`.github/workflows/daily-eval-gate-monitor.yml`
- 触发：每天 UTC 01:30（可手动 `workflow_dispatch`）
- 行为：
- 运行回归流水线并刷新看板
- 生成自动风险说明（md/json）
- 执行 gate 检查
- 执行 release policy 双轨检查（`demo` + `prod`，严格模式）
- 若 gate 失败，自动创建或更新“同日唯一”`eval-gate-alert` Issue（避免重复开单）
- 若任一 release policy 失败，也会触发同一告警链路
- 默认 `demo` 失败直接阻断；`prod` 是否阻断由仓库变量 `EVAL_POLICY_ENFORCE_PROD=true/false` 控制
- 自动检查告警 SLA 字段：`Owner` + `DDL(YYYY-MM-DD)`
- SLA 缺失自动加红色标签 `sla-missing` 并评论提醒
- 若连续失败达到 3 天（含当天），自动加 `p1-gate` 标签并 @升级负责人
- 对 open 的 `p1-gate` 告警，超过 24h 仍未恢复时每天自动追加一次复盘提醒评论（按天去重）
- 若 gate 恢复 PASS，自动回写恢复评论并关闭所有 open `eval-gate-alert` Issue
- 配套模板：`.github/ISSUE_TEMPLATE/04-eval-gate-alert.yml`
- 复盘模板：`docs/eval/p1_postmortem_template.md`

告警升级负责人配置：

- GitHub Repo Variables：`EVAL_GATE_ESCALATION_MENTIONS`
- 示例值：`@leilehuimieba @teammate1`
- 若未配置，默认 @仓库 owner

升级阈值配置（可选）：

- `EVAL_GATE_ESCALATION_STREAK_DAYS`：连续失败触发 P1 的天数阈值（默认 `3`）
- `EVAL_GATE_REMINDER_HOURS_LIST`：P1 提醒阶段列表（默认 `24,48`，按小时）
- 示例：`24,48,72`（会在达到对应阶段后按天提醒）

故障分级表（Daily Monitor）：

| 等级 | 触发条件 | 系统动作 | 人工要求 |
|---|---|---|---|
| P3 | 当天首次 gate fail | 创建/更新同日告警单 | 填写 Owner/DDL，开始排障 |
| P2 | gate fail 且 SLA 缺失 | 打 `sla-missing` 红标并提醒评论 | 当日补齐 SLA 字段 |
| P1 | 连续 3 天 gate fail | 打 `p1-gate`，自动 @升级负责人 | 进入优先修复通道，修复后立即回归 |
| P1+24h | P1 告警超过 24h 未恢复 | 每日自动复盘提醒评论 | 提交/更新复盘文档并同步进展 |
| Recovery | gate 恢复 PASS | 自动评论并关闭 open 告警 | 复盘原因，更新预防项 |

周度运行统计：

- 输出文件：`docs/eval/weekly_gate_ops.md`
- 生成脚本：`scripts/generate_weekly_gate_ops.py`
- 自动触发：`.github/workflows/weekly-report.yml`（每周自动 PR）

周度数据扩容（V8）自动化：

- 工作流：`.github/workflows/weekly-v8-data-refresh.yml`
- 触发：每周 UTC 周三 01:20（可手动 `workflow_dispatch`）
- 行为：
- 执行 `scripts/run_v8_release.ps1`
- 校验 `data_sources` 结构
- 自动提交周度数据刷新 PR（`bot/weekly-v8-data-refresh`）

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

## 第十一步：生成 V8.1 可用数据包（skill 抓取链路）

```powershell
powershell -File scripts/run_v8_1_release.ps1
```

- 产物目录：`release_exports/v8.1/`
- 关键文件：
- `release_exports/v8.1/knowledge_base_import_ready.csv`
- `release_exports/v8.1/web_seed_urls_v8_1_prefetch_status.csv`
- `release_exports/v8.1/web_seed_v8_1_prefetch_report.md`

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
- `docs/ops/dify_provider_recovery_and_smoke_cn.md`
- `docs/ops/dify_provider_recovery_acceptance_20260330.md`
- `docs/ops/server_go_live_bundle_cn.md`
- `docs/pipeline/data_source_plan.md`
- `eval_set_v1.csv`
- `eval_criteria.md`
- `retrieval_tuning_report.md`

