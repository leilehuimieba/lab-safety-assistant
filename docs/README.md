# 文档执行入口

## 1. 当前项目口径

- **项目名称**：实验安全前置哨
- **英文名称**：Lab Safety Copilot
- **当前阶段**：Phase 5 - no-Dify 需求重定位与轻量 MVP
- **当前唯一主线**：实验前自查 → 风险判断 → 开工阻断 / 老师确认 → 管理看板

## 2. 默认读取顺序

1. `AGENTS.md`
2. `docs/README.md`
3. `docs/INDEX.md`
4. `docs/roadmap.md`
5. `docs/changes/INDEX.md`
6. active change 的 `status.md`
7. active change 的 `tasks.md`
8. 需要时再读产品文档和运行文档

## 3. 当前文档范围

当前 `docs/` 只保留：

- 当前主线文档
- 当前 active change
- 当前运行与验收文档
- 当前产品设计 / 实现 / 测试 / 答辩材料

所有旧 Dify、v8.2、申报书历史材料已从当前入口移除，不再作为默认执行依据。

## 4. 当前冲突优先级

1. 用户最新明确指令
2. active change 的 `status.md` / `tasks.md`
3. `docs/roadmap.md`
4. `docs/INDEX.md`
5. 本文档
6. 根 `README.md`

## 5. 当前目标

围绕“实验前安全决策”完成最小闭环：

- 学生输入实验信息
- 系统判断风险
- 生成检查清单
- 缺关键项时阻断
- 高风险时提交老师确认
- 管理端可查看统计结果
