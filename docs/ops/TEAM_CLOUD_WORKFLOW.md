# GitHub 云端协作快速入口

本页用于给队友“5分钟上手”。

## 1. 我是新同学，先看哪份文档
按角色直接进入：

1. 信息收集员：`docs/ops/角色1_信息收集员执行手册_v2.md`
2. 清洗与人工审核员：`docs/ops/角色2_数据清洗员执行手册_v2.md`
3. 发布与验收负责人：`docs/ops/角色3_发布与验收负责人执行手册_v1.md`

Word 版下载：

1. `docs/word/角色1_信息收集员执行手册_v2.docx`
2. `docs/word/角色2_数据清洗员执行手册_v2.docx`
3. `docs/word/角色3_发布与验收负责人执行手册_v1.docx`

## 2. 我只用 GitHub 网页，怎么提交流程
不用本地 Git 也能工作：

1. 打开目标文件（如 `data_sources/document_manifest.csv`）
2. 点击 `Edit this file`
3. 修改后选择 `Create a new branch for this commit`
4. 点击 `Propose changes`
5. 创建 PR，按模板补齐验证项

## 3. 任务从哪里领
在仓库 `Issues` 中用模板创建任务：

1. 数据收集任务
2. 数据清洗与人工审核任务
3. 发布与验收任务

对应标签建议：

1. `data-collection`
2. `data-cleaning`
3. `release-review`
4. `todo`

## 4. 每周固定节奏（建议）
每周执行一次完整闭环：

1. 周一到周三：信息收集员补来源并提交 PR
2. 周四：清洗与人工审核员处理批次并提交 PR
3. 周五：发布负责人做人工问答审核并决定是否发布

## 5. 本项目当前优化优先级（建议）
不先换模型，先稳流程：

1. 数据来源扩充（P0/P1）
2. 清洗规则收敛（OCR/正文起始页/跳页规则）
3. 上线前人工问答审核（强制）
4. 连续 2 个批次稳定后，再做“当前模型 vs 内置模型”对比

## 6. 周报自动生成（推荐）
发布负责人每周可直接运行：

```powershell
python scripts\generate_weekly_team_report.py --repo-root . --since "7 days ago" --until "now"
```

默认输出：

- `docs/weekly_reports/weekly_report_YYYYMMDD.md`

这个周报会自动汇总：

1. 本周提交数和活跃贡献者
2. 收集/清洗/发布相关提交数量
3. 数据规模快照（manifest/web_seed/rules）
4. 最新发布验收状态

## 7. 全AI流水线（当前阶段推荐）
如果当前阶段希望“先全AI闭环，后期再人工抽检”，可直接执行：

1. 操作手册：`docs/ops/AI全自动流水线操作手册_v1.md`
2. 一键脚本：`scripts/run_ai_oneclick.ps1`
3. 结果门禁：`scripts/validate_ai_pipeline_report.py`

