# Verify

## 验证范围
- 验证 `v8.2` 演示主链路是否已被单独冻结成文档
- 验证主入口、固定问题、成功判定、最小保底主线和备用链路是否齐备
- 验证彩排版是否补齐默认时长版本、切换阈值、执行前检查和最小记录要求
- 验证是否已提供真实彩排记录模板和首轮预填稿
- 验证是否已提供“最终现场冻结版（预冻结）”与现场执行卡
- 验证是否已提供最终冻结 Gate 与演示 verify 提交清单
- 验证本地服务/API 级主链路是否可预检通过
- 验证是否已把 API 预检结果转译为浏览器级真实彩排待办清单
- 验证是否已完成一次浏览器自动化主线测试
- 验证是否已基于真实浏览器补查结果冻结唯一上台脚本
- 验证是否已基于 2026-04-16 新工作区下的真实浏览器级主线走查，完成“最终上台演示脚本 + 逐步话术版”冻结
- 验证是否已提供“人工计时彩排执行包”，用于直接承接最后一轮人工计时彩排与 Gate 盖章
- 不覆盖主讲人口播计时 Gate 的最终盖章

## 验证方法
- 手工检查以下文档：
  - `docs/ops/v8_2_demo_flow_freeze_cn.md`
  - `docs/ops/v8_2_demo_final_freeze_cn.md`
  - `docs/ops/v8_2_demo_final_script_cn.md`
  - `docs/ops/v8_2_demo_stage_card_cn.md`
  - `docs/ops/v8_2_demo_timed_rehearsal_execution_pack_cn.md`
  - `docs/roadmap.md`
  - `docs/changes/INDEX.md`
  - `docs/changes/active.txt`
- 运行态检查：
  - `GET http://127.0.0.1:8088/api/meta`
  - `GET http://127.0.0.1:8080/console/api/setup`
  - `docker ps --format "table {{.Names}}	{{.Status}}	{{.Ports}}"`
- 浏览器级主线走查：
  - 打开 `http://127.0.0.1:8088`
  - 进入“智能问答”，输入固定问题 `危险实验开始前最关键的阻断项是什么？`
  - 确认页面实际返回 `链路=dify-workflow`
  - 进入“准入阻断”，生成清单后不勾选关键项直接提交
  - 确认页面实际返回 `清单阻断，暂不可开工`
  - 进入“培训与看板”，确认可指出固定 4 类信息
  - 对“培训与看板”页补截图证据
- 对照背景文档：
  - `docs/eval/v8_2_release_summary.md`
  - `docs/eval/formal_acceptance_20260331.md`
  - `docs/ops/demo_script.md`
  - `docs/ops/demo_freeze_runbook_cn.md`

## 预期结果
- 预期 1：演示主入口已明确
- 预期 2：固定问题和固定场景已明确
- 预期 3：成功判定已明确
- 预期 4：最小保底主线和备用链路已明确
- 预期 5：当前主推进 change 与路线图一致
- 预期 6：彩排版微调后，现场切换条件和版本选择规则已明确
- 预期 7：真实彩排结果已有承接模板，后续反馈不会散落丢失
- 预期 8：现场执行已收敛成单一主线，不再依赖多份脚本临场拼接
- 预期 9：真实彩排结束后，有明确 Gate 可判断能否正式盖章
- 预期 10：在真实彩排前，至少已确认本地服务与关键主链路接口不是硬阻塞
- 预期 11：浏览器级真实彩排前，已明确哪些项需要重点观察，避免无效反复测试
- 预期 12：至少已有一次“像人一样点页面”的测试结果，可验证 UI 层主线可跑通
- 预期 13：最终上台演示脚本与逐步话术版已收敛到新工作区当前实际可演示链路
- 预期 14：最后一轮人工计时彩排与 Gate 盖章路径已收敛为单一执行包，不再依赖口头解释串联多份文档

## 实际结果
- 实际 1：演示主入口、标准顺序和固定输入已写入冻结文档
- 实际 2：最小保底主线和备用链路已明确
- 实际 3：当前主推进 change 已切换回 `2026-04-14-v8-2-demo-flow-freeze`，并与 `docs/roadmap.md` 当前主推进口径一致
- 实际 4：冻结文档已补充 5 分钟标准版、3 分钟快演版、切换阈值、执行前检查和彩排记录最低要求
- 实际 5：已新增真实彩排记录模板与首轮预填稿，可直接承接第一次计时彩排
- 实际 6：已新增“最终现场冻结版（预冻结）”和现场执行卡，默认现场主线已收敛为 `web_demo` 总览 -> 问答 -> 阻断 -> 看板 -> 收口
- 实际 7：已新增最终冻结 Gate 与 verify 清单，真实彩排后可直接判断是否允许升级为最终冻结版
- 实际 8：已对齐首轮彩排记录稿与最终现场冻结版，当前默认口径统一为“直接 `web_demo` 开场，事故复盘默认不进主线”
- 实际 9：已对齐通用彩排记录模板与最终现场冻结版，后续轮次记录默认继续沿当前现场主线
- 实际 10：已将 T10 继续细拆为 T10-1 ~ T10-4，后续最终冻结流程已具备显式任务树
- 实际 11：已完成一次本地服务/API 级主链路预检，服务可启动，问答/清单/阻断/看板接口均已返回有效结果
- 实际 12：已新增“浏览器级真实彩排待办清单”，把 API 预检结论转成 T10-1 的直接执行项
- 实际 13：已将首轮彩排记录稿增强为“浏览器真实彩排回填版”，后续 T10-1 可直接按栏回填
- 实际 14：已完成一次浏览器自动化主线测试，页面点击层面的问答/阻断/看板交互可跑通，但当前问答展示仍是 fallback
- 实际 15：已完成 2026-04-16 浏览器级补查，确认：
  - `lab` 问答可稳定返回 `链路=dify-workflow`
  - 准入阻断页可继承当前问题并提交出“清单阻断，暂不可开工”
  - 培训与看板页可稳定展示现成看板数据
  - 事故复盘页虽可打开，但当前无现成记录，不适合作为默认主线步骤
- 实际 16：已据此冻结唯一上台脚本口径：
  - `docs/ops/v8_2_demo_final_freeze_cn.md`
  - `docs/ops/v8_2_demo_final_script_cn.md`
  - `docs/ops/v8_2_demo_stage_card_cn.md`
  默认主线更新为：`平台总览 -> lab 问答 -> 准入阻断 -> 培训与看板 -> 指标收口`
- 实际 17：2026-04-16 新工作区下再次完成运行态确认：
  - `http://127.0.0.1:8088/api/meta` 返回 `app_version = defense-freeze-20260331`、`formal_eval_score = 20/20`、`stability_status = 3/3 PASS`、`runtime_model = gpt-5.3-codex`
  - `http://127.0.0.1:8080/console/api/setup` 返回 `step = finished`
  - Docker 侧 `docker-nginx-1 / docker-api-1 / docker-web-1 / docker-db_postgres-1 / docker-redis-1 / docker-sandbox-1` 均处于 `Up` 状态，其中 `docker-sandbox-1` 为 `healthy`
- 实际 18：2026-04-16 新工作区下再次完成真实浏览器级主线走查：
  - 平台总览页可稳定展示 `defense-freeze-20260331`、`已封版 / 20/20`、`398 导入 / 96 本地`、`Dify 正式知识库工作流`
  - 智能问答页输入固定问题 `危险实验开始前最关键的阻断项是什么？` 后，页面实际返回 `链路=dify-workflow`
  - 准入阻断页点击“基于当前问题生成清单”后，不勾选关键项直接提交，页面实际返回 `清单阻断，暂不可开工`
  - 培训与看板页可稳定指出 `清单阻断率 90% / 培训通过率 0% / 低置信问题 5 条 / 最近高风险场景`
- 实际 19：已按上述走查结果收敛最终文档口径：
  - `docs/ops/v8_2_demo_final_freeze_cn.md` 已明确“脚本与逐步话术已冻结，主讲人口播计时 Gate 待盖章”
  - `docs/ops/v8_2_demo_final_script_cn.md` 已明确当前逐步话术版以新工作区浏览器级主线走查为复核依据
- 实际 20：已新增 `docs/ops/v8_2_demo_timed_rehearsal_execution_pack_cn.md`，将最后一轮人工计时彩排的角色分工、计时起止点、逐步执行、回填要求、verify 清单与 freeze gate 判定路径收敛为单一执行包

## 证据
- 文档证据：
  - `docs/ops/v8_2_demo_flow_freeze_cn.md`
  - `docs/ops/v8_2_demo_final_freeze_cn.md`
  - `docs/ops/v8_2_demo_final_script_cn.md`
  - `docs/ops/v8_2_demo_stage_card_cn.md`
  - `docs/ops/v8_2_demo_timed_rehearsal_execution_pack_cn.md`
  - `docs/ops/demo_rehearsal_record_template_cn.md`
  - `docs/ops/v8_2_demo_rehearsal_round1_draft_cn.md`
  - `docs/ops/v8_2_demo_freeze_gate_cn.md`
  - `docs/ops/v8_2_demo_verify_checklist_cn.md`
  - `docs/roadmap.md`
  - `docs/changes/INDEX.md`
  - `docs/changes/active.txt`
  - `docs/changes/2026-04-14-v8-2-demo-flow-freeze/status.md`
  - `docs/changes/2026-04-14-v8-2-demo-flow-freeze/tasks.md`
- 运行态证据：
  - `GET http://127.0.0.1:8088/api/meta`
  - `GET http://127.0.0.1:8080/console/api/setup`
  - `docker ps --format "table {{.Names}}	{{.Status}}	{{.Ports}}"`
- 截图 / 页面证据：
  - `artifacts/browser-regression/2026-04-16-platform-overview.png`
  - `artifacts/browser-regression/2026-04-16-lab-lane.png`
  - `artifacts/browser-regression/2026-04-16-gate-workspace.png`
  - `artifacts/browser-regression/2026-04-16-demo-freeze-training-and-dashboard.png`
- 背景证据：
  - `docs/eval/v8_2_release_summary.md`
  - `docs/eval/formal_acceptance_20260331.md`
  - `docs/ops/demo_script.md`
  - `docs/ops/demo_freeze_runbook_cn.md`

## 未通过项
- 未通过项 1：尚未完成带主讲话术的人工计时彩排，因此还不能以本 verify 直接宣称“最终 Gate 已盖章”

## 结论
- pass-with-followups
- 允许继续进入最后一轮主讲人口播计时彩排，并在彩排后用 freeze gate 做最终盖章判断
