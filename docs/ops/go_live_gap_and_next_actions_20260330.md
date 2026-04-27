# 项目落地差距与推进计划（2026-03-30）

## 1. 当前已具备（可演示）

- `demo/prod` 双轨发布门禁已通过（strict）。
- `v8.1` 导入包已产出，可直接用于知识库导入。
- Web 演示服务可本地/服务器启动（`web_demo` + `deploy/*.sh`）。
- 有日常质量门禁、发布策略校验、周报自动化工作流。

## 2. 距离“稳定落地”还差什么

以下按上线优先级排序：

1. 运行时健康巡检未完全自动化  
   说明：目前 embedding 通道在部分环境会不稳定，导致需要 `--skip-health-check` 临时绕过。

2. 发布前统一体检入口缺失  
   说明：之前需要人工分别检查门禁、风险说明、导入包和演示服务探活。

3. 上线窗口标准未固化到文档  
   说明：团队成员对“什么叫可上线”没有一个统一的 yes/no 判断口径。

## 3. 本轮已补齐

1. 新增 go-live 预检脚本  
   - `scripts/release/go_live_preflight.py`
   - 自动检查：
     - 最新 one-click 发布结果是否 `success`
     - `demo/prod` 策略是否 `PASS`
     - 风险说明是否满足应急阈值
     - override 是否关闭
     - 发布包关键文件是否齐全
     - Web `/health` 探活是否正常

2. 新增服务器侧一键预检脚本  
   - `deploy/go_live_preflight.sh`

3. 新增 GitHub Actions 手动预检流程  
   - `.github/workflows/go-live-preflight.yml`

## 4. 下一步推进（直接面向落地）

1. 先做“稳定性验证”  
   - 连续 3 轮执行 one-click（相同参数），确保 `prod strict` 连续 PASS。

2. 再做“服务器实链路验收”  
   - 在目标服务器执行：
     - `./deploy/start_web_demo.sh`
     - `./deploy/go_live_preflight.sh`
   - 目标：`go_live_readiness` 为 PASS。

3. 最后做“发布冻结与回滚演练”  
   - 冻结发布包版本（tag + release note）。
   - 演练一次回滚（恢复上一个稳定 workflow backup + 重启 web_demo）。

## 5. 上线口径（建议）

满足以下全部条件才执行对外发布：

1. 最新 `run_eval_release_oneclick` 状态为 `success`
2. `docs/eval/release_policy_check_prod.json` 为 `PASS`
3. `docs/eval/eval_dashboard_gate_override.json` 中 `enabled=false`
4. `docs/ops/go_live_readiness.json` 中 `overall=PASS`
5. Web 入口 `/health` 连续 5 分钟可用

