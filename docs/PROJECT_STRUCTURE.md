# 项目目录结构与分工说明

本文档用于统一项目内文件放置规范，避免“文件越做越散、队友找不到入口”。

## 1. 目录分层（当前标准）

```text
lab-safe-assistant-github/
├─ docs/                    # 文档中心（手册、流程、报告）
│  ├─ guides/               # 快速入门与规则说明
│  ├─ proposal/             # 立项书与申报材料
│  ├─ reports/              # 阶段报告与过程复盘
│  ├─ word/                 # 面向成员分发的 Word 手册
│  └─ *.md                  # 运行、流程、SOP 等主文档
├─ templates/               # 结构模板（KB、Eval、Schema）
├─ scripts/                 # 自动化脚本（采集、清洗、评测、门禁）
├─ data_sources/            # 种子链接、manifest、预抓取状态
├─ manual_sources/          # 人工补录资料（inbox/approved/rejected）
├─ artifacts/               # 脚本运行产物（可再生成）
├─ web_demo/                # 演示页面与接口
├─ knowledge_base_curated.csv
├─ safety_rules.yaml
└─ eval_set_v1.csv
```

## 2. 放置规则（必须遵守）

1. 新增模板文件一律放 `templates/`，不要再放仓库根目录。
2. 阶段性报告统一放 `docs/reports/`，命名建议 `*_report.md`。
3. 申报书、结题书等材料统一放 `docs/proposal/`。
4. 快速上手类文档统一放 `docs/guides/`。
5. 新增脚本统一放 `scripts/`，并在脚本开头写用途说明。
6. 运行产物放 `artifacts/`，可重复生成的中间文件不要提交到根目录。

## 3. 角色协作入口

1. 信息收集员：`docs/角色1_信息收集员执行手册_v2.md`
2. 数据清洗员：`docs/角色2_数据清洗员执行手册_v2.md`
3. 发布负责人：`docs/角色3_发布与验收负责人执行手册_v1.md`
4. 云端协作总入口：`docs/TEAM_CLOUD_WORKFLOW.md`

## 4. 提交流程建议

1. 每次提交只改一类内容（例如“只改采集清单”或“只改清洗脚本”）。
2. 提交前执行：
   - `python scripts/quality_gate.py`
3. Pull Request 标题建议：
   - `docs: ...`
   - `data: ...`
   - `scripts: ...`
   - `feat: ...`

## 5. 后续可选优化

1. 将 `docs` 根目录继续细分为 `docs/ops`、`docs/pipeline`、`docs/eval`（第二阶段再做）。
2. 将 `scripts` 按功能拆为子目录（`scripts/ingest`、`scripts/eval`、`scripts/governance`）。
3. 增加一个自动检查：阻止把新文件直接丢到仓库根目录（除白名单外）。
