# v4 二轮修复报告

- 生成时间：`2026-03-27T22:04:32+08:00`
- 运行目录：`D:\workspace\lab-safe-assistant-github\artifacts\v4_2_repair_round\run_20260327_220339`
- 输入数据：`D:\workspace\lab-safe-assistant-github\artifacts\relink_v4_2\relink_success_kb_candidates_structured.csv`

## 审核通过率变化

| 阶段 | 总条目 | 通过条目 | 通过率 | 调用错误率 | 解析错误率 |
|---|---:|---:|---:|---:|---:|
| baseline audit | 3 | 3 | 100.00% | 0.00% | 0.00% |
| second audit | 3 | 3 | 100.00% | 0.00% | 0.00% |
| second recheck | 3 | 2 | 66.67% | 0.00% | 0.00% |

## 产物路径

- baseline 聚类：`D:\workspace\lab-safe-assistant-github\artifacts\v4_2_repair_round\run_20260327_220339\baseline_cluster\failure_clusters.md`
- 改写后 CSV：`D:\workspace\lab-safe-assistant-github\artifacts\v4_2_repair_round\run_20260327_220339\rewrite\knowledge_base_rewritten.csv`
- 改写日志：`D:\workspace\lab-safe-assistant-github\artifacts\v4_2_repair_round\run_20260327_220339\rewrite\rewrite_log.csv`
- second 聚类：`D:\workspace\lab-safe-assistant-github\artifacts\v4_2_repair_round\run_20260327_220339\second_cluster\failure_clusters.md`
- 二轮复检通过 CSV：`D:\workspace\lab-safe-assistant-github\artifacts\v4_2_repair_round\run_20260327_220339\second_recheck\knowledge_base_recheck_pass.csv`