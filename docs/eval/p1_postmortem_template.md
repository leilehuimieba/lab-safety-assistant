# P1 Gate 故障复盘模板

适用范围：`eval-gate-alert` 且带 `p1-gate` 标签的事件。  
建议在告警触发后 24 小时内提交首版复盘，恢复后 48 小时内补全最终版。

建议文件命名：

- `docs/eval/postmortems/YYYY-MM-DD_issue-<issue_number>.md`

---

## 1. 事件信息

- Issue: `<#number>`
- 事件等级: `P1`
- 负责人（Owner）:
- 协同人员:
- 首次触发时间:
- 恢复时间:
- 持续时长:

## 2. 现象与影响

- 现象摘要（用户/系统层面）:
- 影响范围（评测、发布、值班）:
- 受影响指标（例如 route_success_rate / timeout_rate）:

## 3. 时间线（Timeline）

按时间顺序记录关键动作：

- `HH:MM` 发现告警
- `HH:MM` 初步排查
- `HH:MM` 临时缓解措施
- `HH:MM` 根因确认
- `HH:MM` 永久修复
- `HH:MM` 回归验证通过

## 4. 根因分析（RCA）

- 直接原因:
- 深层原因:
- 为什么之前未被提前发现:
- 相关证据（日志/截图/指标链接）:

## 5. 修复与验证

- 已实施修复:
- 回滚/兜底方案:
- 验证方法:
- 验证结果:

## 6. 预防项（Action Items）

至少包含 3 类：

- 监控与告警改进:
- 流程与门禁改进:
- 数据与模型质量改进:

格式建议：

- [ ] Action-1（Owner: @xxx，DDL: YYYY-MM-DD）
- [ ] Action-2（Owner: @yyy，DDL: YYYY-MM-DD）
- [ ] Action-3（Owner: @zzz，DDL: YYYY-MM-DD）

## 7. 结论

- 是否可恢复正常发布节奏:
- 后续观察窗口（天）:
- 复盘结论摘要:
