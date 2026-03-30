# 优先级执行报告（2026-03-30）

## 执行目标

按优先级顺序推进：

1. A：发布可用性（实时回归 + 门禁）
2. B：可持续供数（V8 扩容链路）
3. C：平台化运营（看板/自动化）

## A 阶段（发布可用性）

- 执行命令：
  - `powershell -File scripts/run_v7_dify_demo_chain.ps1 -SkipImport -EvalLimit 20`
- 结果：阻塞（未完成实时回归）
- 阻塞原因：
  - 当前环境 Docker API 不可用，无法从 Dify 数据库自动提取 `AppApiKey`
  - 未提供 `DIFY_APP_API_KEY` 环境变量
- 已完成的修复：
  - `scripts/run_v7_dify_demo_chain.ps1` 增加 AppKey 获取兜底顺序：
    - `-AppApiKey` 参数
    - `DIFY_APP_API_KEY` 环境变量
    - Docker 可用时才尝试 DB 自动提取
  - Docker 不可用时给出明确提示，避免硬报错噪音

## B 阶段（可持续供数）

- 执行命令：
  - `powershell -File scripts/run_v8_release.ps1`
- 结果：成功
- 关键产物：
  - `release_exports/v8/knowledge_base_import_ready.csv`
  - `docs/pipeline/web_seed_v8_prefetch_report.md`
  - `data_sources/web_seed_urls_v8_prefetch_status.csv`
- 本次统计：
  - 预抓取：`0/30` 可抓取，`30/30` 被拦截（主要为 403）
  - 生成知识条目：`109`
  - 导入包总条目：`459`

## C 阶段（平台化运营）

- 已完成：
  - 刷新发布就绪看板与阻断 TopN：
    - `docs/eval/release_readiness_dashboard.md`
    - `docs/eval/release_blocker_topn.md`
    - `docs/ops/release_fix_plan_auto.md`
  - 新增低置信队列看板脚本：
    - `scripts/generate_low_confidence_dashboard.py`
    - 输出：
      - `docs/eval/low_confidence_dashboard.json`
      - `docs/eval/low_confidence_dashboard.md`
  - 自动化工作流增强：
    - `daily-eval-gate-monitor.yml` 增加低置信看板生成与产物上传
    - `weekly-report.yml` 增加低置信看板生成
    - 新增 `weekly-v8-data-refresh.yml`（每周自动跑 V8 扩容并开 PR）
  - 修复发布修复计划生成器重复任务号问题：
    - `scripts/generate_release_readiness_dashboard.py` 改为全局唯一 `task_id` 分配

## 质量检查

- `python -m pytest -q`：通过
- `python scripts/quality_gate.py --repo-root . --skip-secret-scan`：通过
- `python scripts/validate_release_fix_plan.py --repo-root .`：通过

## 下一步恢复命令（A 阶段继续）

1. 准备 AppKey（任选一种）：
   - 设置环境变量：`set DIFY_APP_API_KEY=<app-xxxx>`
   - 或命令参数：`-AppApiKey <app-xxxx>`
2. 重跑实时链路：
   - `powershell -File scripts/run_v7_dify_demo_chain.ps1 -SkipImport -EvalLimit 20`
3. 重跑发布看板：
   - `python scripts/generate_release_readiness_dashboard.py --repo-root . --profiles demo,prod --strict-profiles demo,prod`
