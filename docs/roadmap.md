# 项目路线图

## 1. 当前阶段
- 当前阶段：Phase 1 - 演示主链路固化
- 阶段状态：进行中
- 当前目标：
  1. 冻结 `v8.2` 演示主入口和标准顺序
  2. 固定现场问题集、场景输入和成功判定
  3. 明确最小保底主线与备用链路
  4. 为后续彩排和答辩验收提供统一执行依据
  5. 收敛本地 / 服务器目录职责与同步边界，避免服务器演示目录继续分叉
  6. 完成 `v8.2` 最终主讲人口播计时彩排与 freeze gate 盖章
- 当前主推进 change：`docs/changes/2026-04-14-v8-2-demo-flow-freeze/`

## 2. 阶段列表

### Phase 0 - 治理底盘收口
- 目标：统一执行入口、阶段口径、change 机制、AI 协作规则
- 输入：现有 README / eval / ops / reports / proposal 文档
- 交付物：
  - `AGENTS.md`
  - `docs/README.md`
  - `docs/roadmap.md`
  - `docs/changes/README.md`
  - `docs/changes/INDEX.md`
  - `docs/templates/*.md`
- Gate：
  - 当前主线明确
  - 当前阶段明确
  - 当前 active change 明确
  - AI 可按统一读取顺序推进
- 失败回退：
  - 回退到“仅保留现有 docs，不改变业务结构”的最小状态

### Phase 1 - 演示主链路固化
- 目标：固定 `v8.2` 演示基线与复现步骤
- 输入：`release_exports/v8.2/`、`web_demo/`、`scripts/`、`docs/eval/`、`docs/ops/`
- 交付物：
  - 演示脚本
  - 主链路 verify
  - 关键命令与截图 / 证据
  - 本地 / 服务器同步与部署边界规范
- Gate：
  - demo 主链路可复现
  - 关键问题集可稳定演示
  - 答辩讲解口径一致
  - 本地与服务器同步范围清晰
- 失败回退：
  - 回退到上一个可演示版本和脚本

### Phase 2 - 答辩材料与演示验收
- 目标：完成答辩可讲、可演、可答疑
- 输入：Phase 1 固化结果
- 交付物：
  - 答辩要点
  - 指标说明
  - 常见问题回答材料
- Gate：
  - 演示链路、文档、话术一致
  - 关键指标和证据可快速出示
- 失败回退：
  - 回退为“精简演示版本”，缩小讲解范围

### Phase 3 - 可选平台化增强
- 目标：推进稳定化、健康检查、prod 收敛、回滚演练
- 输入：展示阶段稳定成果
- 交付物：
  - prod gate 修复
  - 服务器实链路验收
  - 回滚演练记录
- Gate：
  - readiness 满足要求
  - 回滚路径已验证
- 失败回退：
  - 保留展示主线，不阻塞课程交付

## 3. 阶段切换规则
进入下一阶段前必须满足：
- 当前阶段交付物齐全
- 当前阶段 Gate 明确通过
- 相关 change 已收口或冻结
- `verify.md` 证据已补齐

## 4. 当前里程碑口径
- 课程 / 大创展示优先
- `v8.2` 作为当前演示数据 / 发布基线
- `prod` 严格门禁与 go-live readiness 保留为后续增强项，不作为当前阶段首要 Gate
- 当前答辩口径以 `docs/ops/defense_alignment_cn.md` 为总入口
- 当前演示链路收敛入口以 `docs/ops/v8_2_demo_flow_freeze_cn.md` 为准
- 当前正式上台执行入口以 `docs/ops/v8_2_demo_final_freeze_cn.md` 为准
- 当前本地 / 服务器目录与同步口径已冻结，规范以 `docs/ops/local_server_sync_plan_cn.md` 为准
