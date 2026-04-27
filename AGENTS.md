# AGENTS.md

## 1. 回答语言
- 默认使用简体中文。
- 代码、命令、日志、错误信息保持原语言。
- 用户明确要求英文时再切换。

## 2. 项目默认定位
- 项目名称：实验室安全小助手。
- 主仓库：`D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github`
- 当前优先级：课程 / 大创展示优先。
- 当前演示基线版本：`v8.2`
- 当前首要目标不是 prod 正式上线，而是演示主链路、文档口径和验证证据收敛。

## 3. 默认先检查状态再实现
收到项目推进类请求时，默认先判断：
1. 当前阶段是什么。
2. 当前 active change 是什么。
3. 当前任务做到哪一步。
4. 当前缺什么信息。
5. 是否已经具备继续实现条件。

在未确认上述信息前，不直接进入业务编码。

## 4. 项目推进类请求的默认读取顺序
默认按以下顺序读取：
1. `AGENTS.md`
2. `docs/README.md`
3. `docs/roadmap.md`
4. `docs/changes/INDEX.md`
5. active change 的 `status.md`
6. active change 的 `tasks.md`
7. 如需方案，再读 `design.md`
8. 如需验收，再读 `verify.md`

如需背景信息，再读：
- `README.md`
- `docs/reports/PROJECT_STATUS.md`
- `docs/PROJECT_STRUCTURE.md`
- 相关 `docs/eval/`、`docs/ops/`、`docs/pipeline/`

## 5. 唯一执行入口规则
- `docs/README.md` 是唯一执行入口。
- 根 `README.md` 负责项目介绍与快速运行，不负责日常推进口径。
- `docs/INDEX.md` 是文档地图，不是执行入口。
- `docs/archive/` 下文档默认只读，不作为当前执行依据。

## 6. 文档冲突优先级
冲突时按以下顺序处理：
1. 用户最新明确指令。
2. 当前 active change 的 `status.md` / `tasks.md`。
3. 当前 active change 的 `design.md`。
4. `docs/roadmap.md`。
5. `docs/README.md`。
6. 最新日期的门禁、验收、go-live、release 证据文档。
7. `docs/reports/PROJECT_STATUS.md`、`docs/PROJECT_STRUCTURE.md`。
8. `docs/archive/` 历史文档。

## 7. 中等以上任务必须进入 change 工作区
以下任务必须建 change：
- 影响 `v8.2` 演示链路。
- 影响发布包 / 知识库版本 / 验证口径。
- 影响 `web_demo`、`scripts`、`docs/ops`、`docs/eval`。
- 跨多个文件或多个模块。
- 跨会话推进。
- 涉及结构性设计、回退、验证的任务。
- 任何中等及以上任务。

纯错字、纯格式、无行为变化的小修可不建 change。

## 8. 继续任务时优先读取当前 active change
- 默认只推进 `docs/changes/INDEX.md` 中标记的主推进 change。
- 若没有主推进 change，先补 change，不直接开始中等以上任务。
- 多个 change 并行时，不得跳过主推进 change 直接扩 scope。

## 9. 缺关键信息时先报缺口，不直接编码
出现以下缺口时，先输出缺口清单和建议，不直接进入编码：
- 缺 `proposal.md`
- 缺 `design.md`
- 缺 `tasks.md`
- 缺 `status.md`
- 缺 `verify.md`
- 缺阶段目标
- 缺验收标准
- 缺风险与回退

## 10. 默认输出格式
在项目推进类请求中，优先输出：
- 当前状态
- 缺失项
- 下一步建议

必要时再补充：
- 当前阶段
- 当前 active change
- 当前阻塞
- 验证建议

## 11. 实现后的同步要求
完成中等及以上任务后，至少同步更新：
- 当前 change 的 `tasks.md`
- 当前 change 的 `status.md`
- 当前 change 的 `verify.md`
- 如影响阶段推进，更新 `docs/roadmap.md`
- 如影响执行主线，更新 `docs/README.md`

## 12. 验证前必须补的证据
在宣称“完成”“可演示”“可进入下一阶段”前，必须补齐：
- 验证范围
- 验证方法
- 预期结果
- 实际结果
- 证据位置

没有 verify 证据，不得宣称闭环完成。

## 13. 展示优先规则
- 当前阶段以课程 / 大创展示可复现为首要标准。
- 若 prod 能力与展示主线冲突，优先保住展示主线。
- 非必要不引入重型基础设施或大规模重构。
- 所有扩展必须说明它如何服务当前展示主线，否则后置。

## 14. 禁止行为
禁止以下行为：
- 跳过 verify 直接宣布完成。
- 跳过阶段 Gate 直接进入下一阶段。
- 中等以上任务不建 change。
- 缺 status / tasks 时直接续做。
- 擅自扩大 scope。
- 为了“更完整”引入与展示主线无关的大改。
- 用历史文档覆盖当前 active change 口径。
- 信息不足时硬写业务代码。

## 15. 轻量但严格
- 规范要求严格，但结构保持最小可用。
- 优先兼容现有仓库，不做目录级重建。
- 先收敛主线，再扩平台化能力。
