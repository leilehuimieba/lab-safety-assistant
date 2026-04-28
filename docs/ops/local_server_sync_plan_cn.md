# 本地 / 服务器目录与同步规范（当前执行版）

> 用途：统一说明“本地项目目录怎么规划、服务器目录怎么规划、本地与服务器有什么差别、后续应该怎么同步”。  
> 优先级：若历史部署文档与本文冲突，当前以本文为准；若与用户最新明确指令冲突，以用户指令为准。  
> 当前默认本地事实源：`D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github`

## 1. 当前结论先说清

当前项目建议按 **四层结构** 理解：

1. **主仓库层（唯一事实源）**：本地新工作区仓库
2. **本地运行层**：本机 Dify、截图、日志、临时输出等
3. **服务器部署层**：服务器上唯一正式运行目录
4. **服务器历史快照层**：仅作回退或历史证据，不作为默认运行入口

当前推荐口径：

- 本地唯一事实源：`D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github`
- 服务器唯一正式部署目录：`/root/lab-safe-assistant-github`
- 服务器历史快照目录：`/root/lab-safe-assistant-github-release`（只应保留为快照 / 回退点，不应长期继续充当默认运行目录）

---

## 2. 当前本地与服务器实际差异

### 2.1 本地当前实际结构特点

当前本地仓库除常规代码 / 文档外，还包含：

- `docs/changes/`：当前 active change 工作区
- `docs/templates/`：change 模板
- `docs/archive/`、`docs/weekly_reports/`
- `local_env/`：本地 Dify Docker 环境
- `artifacts/`：浏览器截图、回归证据、运行态留档
- `logs/`、`output/`：本地运行产物
- `.venv312/`、`_tmp_*`：本地环境与临时文件

这些内容说明：**本地仓库不仅是代码仓库，也是当前项目治理、演示验证和本地运行事实源。**

### 2.2 服务器当前实际结构特点

服务器当前同时存在：

- `/root/lab-safe-assistant-github`
- `/root/lab-safe-assistant-github-release`

而且当前 `web_demo` 实际运行进程来自：

- `/root/lab-safe-assistant-github-release`

这意味着：

- 服务器“源码目录”和“运行目录”已分叉
- 服务器当前能跑，但后续如果继续无规则同步，极易改错目录

### 2.3 当前差异的核心判断

当前差异不是“内容多一点少一点”的问题，而是：

1. **本地是最新事实源**
2. **服务器当前运行目录不是推荐正式目录**
3. **本地运行产物与本地环境不能原样推上服务器**
4. **后续必须先收敛目录职责，再谈同步**

---

## 3. 标准目录规划

## 3.1 主仓库层（唯一事实源）

位置：

- `D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github`

职责：

- 保存代码
- 保存文档
- 保存 deploy 脚本
- 保存发布包与知识库数据
- 保存当前 change 治理结构

主仓库层应长期保留的内容：

```text
lab-safe-assistant-github/
├─ AGENTS.md
├─ README.md
├─ docs/
├─ deploy/
├─ scripts/
├─ web_demo/
├─ tests/
├─ data_sources/
├─ manual_sources/
├─ release_exports/
├─ skills/
├─ knowledge_base_curated.csv
├─ safety_rules.yaml
└─ eval_set_v1.csv
```

### 说明

- 这是当前唯一默认事实源
- 后续所有服务器同步都应从这里出发
- 不应再从旧 `D:\workspace` 或服务器目录反向覆盖本地

---

## 3.2 本地运行层（仅本地使用）

职责：

- 承载本机 Dify / 本机 web_demo / 浏览器级验证 / 临时产物
- 便于本地彩排、截图、回归和调试
- 不作为服务器标准同步内容

本地运行层典型目录：

```text
local_env/
artifacts/
logs/
output/
.venv*/
_tmp_*/
.env.web_demo
```

### 说明

这些内容：

- 可以存在于本地仓库旁边或仓库内
- 但**不应直接原样打包推上服务器**
- 其中 `local_env/` 明确属于“本地 Dify 环境”，不是服务器部署主干

---

## 3.3 服务器部署层（唯一正式运行目录）

推荐正式目录：

- `/root/lab-safe-assistant-github`

职责：

- 作为服务器唯一正式部署目录
- 保存服务器端 `.env.web_demo`
- 承载 `deploy/start_web_demo.sh`、`deploy/status_web_demo.sh`、systemd 等正式运行入口

服务器部署层应保留的内容：

```text
/root/lab-safe-assistant-github/
├─ web_demo/
├─ deploy/
├─ docs/
├─ scripts/
├─ data_sources/
├─ release_exports/
├─ README.md
├─ .env.web_demo
├─ logs/
└─ run/
```

### 说明

- 服务器部署层应只保留“可运行需要的最小集合”
- `.env.web_demo`、日志、run 目录由服务器本机保留
- 后续 smoke check、go-live preflight、systemd 都应围绕这一个目录执行

---

## 3.4 服务器历史快照层（只保留为回退点）

当前存在目录：

- `/root/lab-safe-assistant-github-release`

建议定位：

- 历史快照
- 回退点
- 运行收口前的旧版本证据目录

### 说明

- 该目录不应再长期充当默认运行入口
- 真正执行收口时，应先把当前运行目录切回正式部署层，再决定：
  - 删除
  - 归档改名
  - 仅留备份

---

## 4. 同步白名单 / 黑名单 / 保留项

## 4.1 应同步到服务器的白名单

建议同步：

- `AGENTS.md`（如需保留协作口径）
- `README.md`
- `docs/`
- `deploy/`
- `scripts/`
- `web_demo/`
- `tests/`（如需服务器自检）
- `data_sources/`
- `manual_sources/`（如服务器也要参与资料接收 / 审核）
- `release_exports/`
- `skills/`（仅当服务器也确需本地技能）
- `knowledge_base_curated.csv`
- `safety_rules.yaml`
- `eval_set_v1.csv`

### 推荐理解

这些属于：

- 代码 / 文档 / 数据 / 发布包 / deploy 主干
- 是可以从本地事实源同步到服务器的内容

---

## 4.2 禁止直接同步到服务器的黑名单

以下内容不应原样同步到服务器：

- `local_env/`
- `artifacts/`
- `logs/`
- `output/`
- `.venv/`、`.venv312/`
- `__pycache__/`
- `_tmp_*`
- 本地 `.env.web_demo`
- 本地浏览器截图 / 回归证据
- 本地 Docker 运行态文件

### 原因

这些内容通常是：

- 本地路径绑定
- 本地临时产物
- 本地环境副本
- 会污染服务器部署目录

---

## 4.3 服务器必须保留但不应被本地覆盖的内容

以下内容应在服务器本机保留，不应用本地版本覆盖：

- 服务器 `.env.web_demo`
- 服务器 `logs/`
- 服务器 `run/`
- 服务器 systemd 实际配置 / 状态
- 服务器 nginx / caddy 生效配置副本
- 服务器隧道 / 健康检查运行态文件

### 原则

- 本地同步“代码和文档”
- 服务器保留“密钥和运行态”

---

## 5. 当前推荐同步流程

## 5.1 先定唯一服务器正式目录

后续统一按：

- 正式部署目录：`/root/lab-safe-assistant-github`
- 历史快照目录：`/root/lab-safe-assistant-github-release`

执行同步前，先确认：

- 当前正在跑的进程是否仍绑定 release 目录
- 当前 `.env.web_demo` 在哪个目录里
- 当前日志和 pid 文件在哪个目录里

---

## 5.2 从本地主仓库打“最小部署包”

建议只打包白名单内容，例如：

```text
web_demo/
deploy/
docs/
scripts/
data_sources/
release_exports/
manual_sources/
README.md
AGENTS.md
knowledge_base_curated.csv
safety_rules.yaml
eval_set_v1.csv
```

不要把以下内容打进部署包：

```text
local_env/
artifacts/
logs/
output/
.venv*/
_tmp_*/
.env.web_demo
```

---

## 5.3 服务器先做回退点

真正同步前，建议先在服务器上：

1. 备份当前正式目录 / 运行目录
2. 备份当前 `.env.web_demo`
3. 保留当前日志目录
4. 明确回退命令或回退路径

只有回退点明确后，再覆盖内容。

---

## 5.4 解压到唯一正式目录

同步后的目标目录应统一为：

- `/root/lab-safe-assistant-github`

同步完成后：

- 把服务器原有 `.env.web_demo` 放回
- 确认 `deploy/start_web_demo.sh` 仍从该目录运行
- 确认 systemd / status 脚本目标目录一致

---

## 5.5 启动并最小验证

同步后至少执行：

```bash
cd /root/lab-safe-assistant-github
./deploy/start_web_demo.sh
./deploy/status_web_demo.sh
curl -sS http://127.0.0.1:8088/health
```

再检查：

- 进程实际来自哪个目录
- `/health` 是否返回 `{"status":"ok"}`
- 页面是否能打开
- `.env.web_demo` 是否没有被覆盖成错误版本

---

## 5.6 成功后再处理旧 release 目录

确认 `/root/lab-safe-assistant-github` 已成功接管运行后，再决定如何处理：

- `/root/lab-safe-assistant-github-release`

建议顺序：

1. 先停旧目录进程
2. 确认正式目录运行正常
3. 再把 release 目录改名为快照目录或归档

---

## 6. 当前对比结论（给老师 / 评委 / 团队的简版回答）

如果有人问：“本地项目和服务器项目有什么区别？怎么同步？”

当前推荐这样回答：

> 现在本地新工作区仓库是唯一事实源，包含代码、文档、演示冻结口径和本地验证证据。服务器侧当前还能正常运行，但历史上保留了一个 release 运行副本，所以目录已经分叉。后续同步不是整仓库无脑覆盖，而是从本地主仓库同步代码、文档、deploy 和发布包；本地运行环境、截图、日志、Dify 本地容器目录不进入服务器。服务器最终会收口成一个正式部署目录，旧 release 目录只作为回退点保留。

---

## 7. 后续建议动作

### 建议 1
先冻结规范，不急着马上动服务器目录。

### 建议 2
下一步如需实操，建议单开一次“服务器目录收口演练”：

- 确认回退点
- 同步最小部署包
- 切换正式运行目录
- 重新检查 health / 日志 / 进程来源

### 建议 3
后续如果要把这套流程完全自动化，再考虑新增：

- 统一同步脚本
- 统一 smoke check 脚本
- 统一服务器切换 runbook
