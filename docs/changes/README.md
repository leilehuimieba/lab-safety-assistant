# Change 工作区说明

## 1. 作用

`docs/changes/` 用于承载当前主线的结构化推进记录：

- proposal
- design
- tasks
- status
- verify

## 2. 当前规则

- 当前只保留**当前有效主线**的 active change
- 所有中等以上改动都应先确认是否需要更新 active change
- 文档、实现、测试、演示材料的结构性调整都应同步 change

## 3. 必备文件

每个 change 至少包含：

- `proposal.md`
- `design.md`
- `tasks.md`
- `status.md`
- `verify.md`

## 4. 完成定义

一个 change 只有在以下条件满足时才可视为完成：

- 目标与范围明确
- 任务清单已收口
- 状态已更新
- 验证证据已记录
- `docs/README.md` / `docs/INDEX.md` / `docs/roadmap.md` 已同步
