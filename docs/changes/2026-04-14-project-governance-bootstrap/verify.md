# Verify

## 验证范围
- 验证本次治理底盘文件是否已落地
- 验证执行入口、路线图、change 工作区和模板是否齐备
- 不覆盖业务功能、发布链路和演示接口的运行验证

## 验证方法
- 手工检查以下文件 / 目录是否存在且内容完整：
  - `AGENTS.md`
  - `docs/README.md`
  - `docs/INDEX.md`
  - `docs/roadmap.md`
  - `docs/archive/README.md`
  - `docs/changes/README.md`
  - `docs/changes/INDEX.md`
  - `docs/changes/active.txt`
  - `docs/changes/2026-04-14-project-governance-bootstrap/`
  - `docs/templates/`
- 检查当前 active change 是否与 `docs/roadmap.md`、`docs/README.md` 的口径一致

## 预期结果
- 预期 1：治理底盘关键文件全部存在
- 预期 2：当前执行主线、当前阶段、当前 active change 可被明确识别
- 预期 3：后续 AI 可根据统一读取顺序开始推进

## 实际结果
- 实际 1：治理底盘关键文件已创建
- 实际 2：当前执行主线已明确为 `v8.2` 展示基线
- 实际 3：当前阶段已明确为 Phase 0，当前 active change 已建立

## 证据
- 证据类型：仓库内新增文件与目录
- 证据位置：
  - `AGENTS.md`
  - `docs/README.md`
  - `docs/roadmap.md`
  - `docs/changes/`
  - `docs/templates/`

## 未通过项
- 无

## 结论
- pass
- 允许继续进入后续基于 change 的项目推进
