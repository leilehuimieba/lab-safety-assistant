# Change 工作区说明

## 1. change 的作用
change 是中等及以上任务的最小推进单元，用于承接 `proposal`、`design`、`tasks`、`status`、`verify`。

## 2. 本项目哪些任务必须建 change
以下任务必须建 change：
- 影响 `v8.2` 演示链路
- 影响发布包 / 知识库版本 / 验证口径
- 影响 `web_demo`、`scripts`、`docs/ops`、`docs/eval`
- 跨多个文件或跨会话推进
- 任何中等及以上任务

以下任务可不建 change：
- 纯错字修正
- 纯格式整理
- 无行为变化的小修补

## 3. 命名规则
目录格式：`YYYY-MM-DD-短名`

示例：
- `2026-04-14-project-governance-bootstrap`
- `2026-04-15-v8-2-demo-flow-freeze`

## 4. 必备文件
每个 change 至少包含：
- `proposal.md`
- `design.md`
- `tasks.md`
- `status.md`
- `verify.md`

## 5. active change 规则
- `docs/changes/INDEX.md` 中只能有一个主推进 change
- `active.txt` 必须与 `INDEX.md` 一致

## 6. 完成定义
一个 change 只有在以下条件满足时才可标记为 `done`：
- 五类文档齐全
- `tasks.md` 完成或明确冻结
- `verify.md` 有证据
- 如影响阶段 Gate，`docs/roadmap.md` 已同步
- 如影响执行主线，`docs/README.md` 已同步

## 7. 禁止行为
- 没有 change 就做中等以上改动
- `status.md` 不更新就继续推进
- 没有 `verify.md` 证据就宣布完成
- 跳过 `proposal.md` / `design.md` 直接做结构性改动
