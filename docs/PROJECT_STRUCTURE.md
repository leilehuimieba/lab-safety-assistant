# 项目结构与文件管理规范

本文件用于约束仓库目录，避免再次出现“历史文件堆积、入口分散、产物混杂”的问题。

## 1. 当前标准目录

```text
lab-safe-assistant-github/
├─ data_sources/                 # 数据源清单与模板（当前主用 v7）
├─ docs/
│  ├─ guides/                    # 快速入门与规则指南
│  ├─ ops/                       # 运行、部署、SOP
│  ├─ pipeline/                  # 抓取/清洗/入库流程
│  ├─ eval/                      # 评测、门禁、发布审核
│  ├─ proposal/                  # 立项申报材料
│  ├─ reports/                   # 阶段报告
│  └─ word/                      # 分发用 Word 文档
├─ release_exports/
│  └─ v7/                        # 当前正式发布包
├─ scripts/                      # 自动化脚本
│  ├─ pipeline/                  # 抓取、清洗、入库主链路脚本
│  ├─ release/                   # 发布打包脚本
│  ├─ qa/                        # 质量门禁脚本
│  └─ *.py                       # 兼容入口（转发到上述子目录）
├─ skills/                       # 本地技能
├─ tests/                        # 回归测试
├─ web_demo/                     # 演示服务
├─ knowledge_base_curated.csv
├─ safety_rules.yaml
└─ eval_set_v1.csv
```

## 2. 文件放置规则

1. 可再生成的运行产物不入仓库根目录。
2. 版本发布产物统一放在 `release_exports/<version>/`。
3. 数据清单统一放在 `data_sources/`，并保留模板文件。
4. 执行说明统一放在 `docs/ops/`，流程说明统一放在 `docs/pipeline/`。
5. 脚本统一放 `scripts/`，测试统一放 `tests/`。

## 3. 清理策略（长期）

1. 保留最新发布版本（例如 `v7`）；旧版本由 Git 历史追溯，不在工作树长期保留。
2. 每轮发布后执行一次仓库清理：
   - 删除历史中间产物
   - 删除过期批次清单
   - 删除失效文档引用
3. 每轮清理后必须执行：
   - `python -m pytest -q`
   - `python scripts/quality_gate.py --repo-root . --skip-secret-scan`

## 4. 脚本调用约定

1. 外部调用优先使用 `scripts/*.py` 兼容入口，避免路径频繁变更导致 CI 和文档失效。
2. 新增脚本按功能放入 `scripts/pipeline`、`scripts/release`、`scripts/qa`。
3. 若脚本升级需要迁移位置，必须保留原入口转发文件，确保历史命令可继续使用。

## 5. 推荐入口

1. 运行总入口：`scripts/run_v7_release.ps1`
2. 发布包入口：`release_exports/v7/knowledge_base_import_ready.csv`
3. 演示入口：`web_demo/app.py`
