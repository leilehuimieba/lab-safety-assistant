# 项目结构与文件管理规范

本文件用于约束仓库目录，避免再次出现“历史文件堆积、入口分散、产物混杂、服务器同步边界不清”的问题。

## 1. 当前标准目录（主仓库层）

当前唯一默认主仓库：

- `D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github`

推荐按下面理解当前标准结构：

```text
lab-safe-assistant-github/
├─ AGENTS.md
├─ README.md
├─ docs/
│  ├─ archive/                  # 历史只读文档
│  ├─ changes/                  # 当前 change 工作区
│  ├─ eval/                     # 评测、门禁、发布审核
│  ├─ guides/                   # 快速入门与规则指南
│  ├─ ops/                      # 运行、部署、SOP、同步规范
│  ├─ pipeline/                 # 抓取/清洗/入库流程
│  ├─ proposal/                 # 立项申报材料
│  ├─ reports/                  # 阶段报告
│  ├─ templates/                # change 模板
│  ├─ weekly_reports/           # 周报类输出
│  └─ word/                     # 分发用 Word 文档
├─ deploy/                      # 服务器部署、systemd、代理、体检脚本
├─ data_sources/                # 数据源清单与模板
├─ manual_sources/              # 手工资料收集与审核工作区
├─ release_exports/             # 版本发布包
├─ scripts/                     # 自动化脚本
│  ├─ demo/
│  ├─ pipeline/
│  ├─ qa/
│  └─ release/
├─ skills/                      # 本地技能
├─ tests/                       # 回归测试
├─ web_demo/                    # 演示服务
│  ├─ data/
│  └─ templates/
├─ knowledge_base_curated.csv
├─ safety_rules.yaml
└─ eval_set_v1.csv
```

## 2. 分层理解（必须区分）

### 2.1 主仓库层

职责：
- 代码、文档、脚本、发布包、change 治理的唯一事实源
- 所有服务器同步默认从这一层出发

### 2.2 本地运行层

典型目录：

```text
local_env/
artifacts/
logs/
output/
.venv*/
_tmp_*/
.env.web_demo
```

职责：
- 本机 Dify
- 本机 `web_demo`
- 浏览器截图 / 回归证据
- 临时运行产物

说明：
- 本地运行层可存在于仓库目录附近或仓库内
- 但不属于服务器标准同步内容

### 2.3 服务器部署层

推荐正式目录：

- `/root/lab-safe-assistant-github`

职责：
- 服务器唯一正式运行目录
- 与 `deploy/start_web_demo.sh`、`status_web_demo.sh`、systemd 绑定

### 2.4 服务器历史快照层

当前已观察到的历史快照目录：

- `/root/lab-safe-assistant-github-release`

职责：
- 回退点 / 历史证据
- 不应长期继续充当默认运行目录

## 3. 文件放置规则

1. 可再生成的运行产物不入主仓库根目录长期保留。
2. 版本发布产物统一放在 `release_exports/<version>/`。
3. 数据清单统一放在 `data_sources/`，并保留模板文件。
4. 执行说明统一放在 `docs/ops/`，流程说明统一放在 `docs/pipeline/`。
5. 脚本统一放 `scripts/`，测试统一放 `tests/`。
6. 服务器同步规范统一参考：`docs/ops/local_server_sync_plan_cn.md`。

## 4. 同步规则（当前必须遵守）

### 4.1 可同步主干

- `docs/`
- `deploy/`
- `scripts/`
- `web_demo/`
- `data_sources/`
- `manual_sources/`
- `release_exports/`
- `README.md`
- `AGENTS.md`
- `knowledge_base_curated.csv`
- `safety_rules.yaml`
- `eval_set_v1.csv`

### 4.2 不应直接推上服务器的内容

- `local_env/`
- `artifacts/`
- `logs/`
- `output/`
- `.venv*/`
- `__pycache__/`
- `_tmp_*`
- 本地 `.env.web_demo`

### 4.3 服务器侧保留项

- 服务器 `.env.web_demo`
- 服务器日志目录
- 服务器 run 目录
- 服务器生效中的 systemd / nginx / caddy 配置副本

## 5. 清理策略（长期）

1. 主仓库保留当前有效结构；历史执行证据通过 `docs/archive/` 或 Git 历史追溯。
2. 本地运行层产物按需清理，但不要混入服务器部署包。
3. 服务器历史快照目录仅作为回退点；完成正式收口后，应避免继续“双目录并行运行”。

## 6. 脚本调用约定

1. 外部调用优先使用 `scripts/*.py` / `scripts/*.ps1` 兼容入口，避免路径频繁变更导致 CI 和文档失效。
2. 新增脚本按功能放入 `scripts/demo`、`scripts/pipeline`、`scripts/release`、`scripts/qa`。
3. 若脚本升级需要迁移位置，必须保留原入口转发文件，确保历史命令可继续使用。

## 7. 推荐入口

1. 项目执行入口：`docs/README.md`
2. 演示主入口：`scripts/start_web_demo_local.ps1`
3. 服务器部署入口：`deploy/start_web_demo.sh`
4. 本地 / 服务器同步规范：`docs/ops/local_server_sync_plan_cn.md`
