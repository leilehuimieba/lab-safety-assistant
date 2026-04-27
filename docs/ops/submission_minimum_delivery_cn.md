# 提交版 / 展示版最小交付清单

> 用途：给课程提交 / 大创展示 / 老师验收时快速说明“最少看什么、打开什么、哪些材料是主材料”。  
> 当前默认工作区：`D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github`  
> 当前展示基线：`v8.2`

## 1. 最小交付目标

本项目当前不是按“生产上线包”交付，而是按“**可运行、可展示、可答辩、可解释**”交付。

因此最小交付清单只覆盖 4 类内容：

1. 能打开的展示入口
2. 能讲清楚的答辩材料
3. 能支撑口径的关键证据
4. 能说明项目结构的最少文档

## 2. 老师 / 评委最少看什么

如果时间很有限，**只看下面 5 项就够**：

1. `docs/ops/defense_alignment_cn.md`
   - 当前答辩总口径总表
2. `docs/ops/v8_2_demo_final_script_cn.md`
   - 当前上台直接照着讲的最终演示脚本
3. `docs/ops/v8_2_demo_stage_card_cn.md`
   - 当前口袋版执行卡
4. `artifacts/browser-regression/2026-04-16-*.png`
   - 浏览器级展示证据截图
5. `http://127.0.0.1:8088`
   - 当前本地展示入口

## 3. 当前最小展示入口

### 默认展示入口
- 页面入口：`http://127.0.0.1:8088`
- 默认工作区：`D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github`

### 默认展示主线
- 平台总览
- lab 问答
- 准入阻断
- 培训与看板
- 指标收口

### 默认不进主线
- README 首页
- 事故复盘完整录入流程
- Dify 后台页面
- 服务器部署页面
- prod / go-live 文档

## 4. 当前最小答辩材料

### 必交答辩材料
1. `docs/ops/defense_alignment_cn.md`
2. `docs/ops/v8_2_demo_final_freeze_cn.md`
3. `docs/ops/v8_2_demo_final_script_cn.md`
4. `docs/ops/v8_2_demo_stage_card_cn.md`
5. `docs/ops/defense_talking_points_cn.md`

### 作用说明
- `defense_alignment_cn.md`：统一口径
- `v8_2_demo_final_freeze_cn.md`：统一演示顺序与边界
- `v8_2_demo_final_script_cn.md`：直接照着讲
- `v8_2_demo_stage_card_cn.md`：现场速看
- `defense_talking_points_cn.md`：回答追问

## 5. 当前最小运行材料

### 必留运行文件
1. `.env.web_demo`
2. `scripts/start_web_demo_local.ps1`
3. `scripts/status_web_demo_local.ps1`
4. `scripts/stop_web_demo_local.ps1`
5. `artifacts/local-web-demo/runtime.json`
6. `web_demo/`

### 必留本地 Dify 相关目录
1. `local_env/dify/docker/`
2. `.env.web_demo.example`
3. `docs/ops/local_workspace_migration_quickstart_cn.md`

## 6. 当前最小证据材料

### 浏览器级证据
1. `artifacts/browser-regression/2026-04-16-platform-overview.png`
2. `artifacts/browser-regression/2026-04-16-lab-lane.png`
3. `artifacts/browser-regression/2026-04-16-agent-lane.png`
4. `artifacts/browser-regression/2026-04-16-dify-workspace.png`
5. `artifacts/browser-regression/2026-04-16-gate-workspace.png`

### 指标与验收证据
1. `docs/eval/v8_2_release_summary.md`
2. `docs/eval/formal_acceptance_20260331.md`
3. `docs/ops/v8_2_demo_api_precheck_20260415_cn.md`
4. `docs/changes/2026-04-15-workspace-migration-to-newwork/verify.md`

## 7. 当前统一指标口径

提交版 / 展示版统一只讲这组数字：

- 知识库正式导入：`398`
- 正式回归：`20/20`
- 稳定性：`3/3 PASS`
- 当前剩余重点：**延迟波动，而不是正确率问题**

## 8. 如果要打包给老师，建议最少包含什么

建议最少包含以下目录 / 文件：

1. `README.md`
2. `docs/README.md`
3. `docs/ops/`
4. `docs/eval/`
5. `docs/changes/2026-04-15-workspace-migration-to-newwork/`
6. `web_demo/`
7. `scripts/`
8. `artifacts/browser-regression/`
9. `artifacts/local-web-demo/runtime.json`
10. `release_exports/v8.2/`
11. `knowledge_base_curated.csv`
12. `safety_rules.yaml`
13. `eval_set_v1.csv`

## 9. 哪些内容不属于“最小交付”

以下内容可以保留在仓库里，但不要求老师第一时间看：

- 历史发布包的全部细节
- Dify 后台配置过程
- 服务器部署细节
- 所有 pipeline 的完整实验记录
- 所有 change 的历史过程文档
- 本地模型切换探索过程

## 10. 给老师 / 评委的一句话说明模板

“这次提交我优先保留了最小可运行展示入口、统一答辩材料、浏览器级展示证据和关键验收文档。也就是说，老师只要看演示入口、最终脚本和关键证据，就能判断这个项目当前已经达到可展示、可答辩、可继续扩展的状态。”
