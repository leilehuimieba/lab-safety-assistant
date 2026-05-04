# 文档索引

## 1. 当前唯一执行入口

- `docs/README.md`：项目执行入口，定义当前主线、阶段、读取顺序和冲突优先级
- `docs/roadmap.md`：当前阶段与阶段 Gate
- `docs/changes/INDEX.md`：当前 active change 总表
- `AGENTS.md`：AI 协作规则

## 2. 当前主推进 change

- `docs/changes/2026-04-28-demand-realignment-no-dify/`
  - 状态：active
  - 目标：暂停 Dify / 申报书主导路线，推进 no-Dify 自研轻量 MVP
  - 关键文件：`proposal.md`、`design.md`、`tasks.md`、`status.md`、`verify.md`

## 3. 当前产品文档

- `docs/product/current_positioning_20260501.md`：当前定位摘要与删旧文档后的统一口径
- `docs/product/prd_lab_safety_copilot_no_dify_20260428.md`：no-Dify PRD
- `docs/product/requirements_spec_20260429.md`：正式需求规格说明书
- `docs/product/design_spec_20260429.md`：系统设计文档
- `docs/product/project_definition_20260428.md`：面向大创/答辩语境的项目定义材料

## 4. 当前验收与运行文档

- `docs/ops/no_dify_mvp_acceptance_checklist.md`：no-Dify MVP 主链路验收清单
- `docs/ops/docker_deploy_guide.md`：Docker 部署说明
- `docs/ops/local_web_demo_windows_quickstart_cn.md`：Windows 本地运行说明
- `docs/guides/README_MVP_START.md`：no-Dify MVP 快速入门
- `docs/guides/safety_rules_guide.md`：YAML 规则引擎维护说明

## 5. 历史 / 证据材料

以下文档保留为历史证据或回退参考，不作为当前主线 Gate：

- `docs/ops/v8_2_*`
- `docs/eval/dify_*`
- `docs/ops/local_dify_bridge_quickstart_cn.md`
- `docs/ops/runbook.md` 中 Dify 相关章节
- `release_exports/v8.2/`

## 6. 模板

- `docs/templates/proposal.template.md`
- `docs/templates/design.template.md`
- `docs/templates/tasks.template.md`
- `docs/templates/status.template.md`
- `docs/templates/verify.template.md`

## 7. 使用说明

- 想知道“现在做什么” → 读 `docs/README.md`
- 想知道“当前阶段” → 读 `docs/roadmap.md`
- 想知道“当前 change 做到哪” → 读 `docs/changes/INDEX.md` 和 active change 的 `status.md`
- 想知道“当前产品到底是什么” → 读 `docs/product/current_positioning_20260501.md`
- 想验收当前 MVP → 读 `docs/ops/no_dify_mvp_acceptance_checklist.md`
