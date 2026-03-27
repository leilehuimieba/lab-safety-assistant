# V4.2 发布链路执行总结（2026-03-27）

## 1. 本轮目标

1. 丢弃上一轮不可访问的 3 条失败源（`WEBV2-001` / `WEBV2-012` / `WEBV3-002`）并替换为可下载来源。
2. 提供 V4.2 一键发布脚本，串联补链、抓取、复检、导出。
3. 产出可直接共享的发布目录 `release_exports/v4.2`。

## 2. 新增脚本与配置

- 补链映射（V4.2）：`data_sources/relink_official_map_v4_2.csv`
- 补链脚本增强（支持自定义输入输出）：`scripts/apply_official_relink.py`
- 补链成功候选构建：`scripts/build_relink_success_candidates.py`
- V4.2 一键发布脚本：`scripts/run_v4_2_release.ps1`

## 3. 替换后的 3 条来源（均可抓取）

1. `WEBV2-001` -> 四川师范大学转载 PDF（高等学校实验室安全规范）
2. `WEBV2-012` -> CCOHS SDS 指南 PDF
3. `WEBV3-002` -> 内蒙古卫健委挂载页（含 WS/T 442 规范 PDF）

对应状态文件中均为 `ok`（见 `artifacts/relink_v4_2/relink_success_ids.csv`）。

## 4. 一键执行结果（run_v4_2_release.ps1）

执行时间：2026-03-27  
修复轮次目录：`artifacts/v4_2_repair_round/run_20260327_204354`

### 抓取结果

- `v1.2`：18/18 `ok`
- `v2.2`：16/17 `ok`
- `v3.2`：14/18 `ok`

非目标失败项（不在本次 3 条替换范围）：

- `WEBV2-016`（blocked）
- `WEBV3-001`（error 412）
- `WEBV3-003`（error 412）
- `WEBV3-004`（error 412）
- `WEBV3-014`（blocked）

### AI 改写/复检（仅针对 V4.2 替换的 3 条）

- baseline audit：`0/3` 通过
- second audit：`0/3` 通过
- second recheck：`0/0`（无进入 recheck 的条目）

说明：本轮 3 条数据的内容结构仍偏原文堆叠，AI 评审分数未达到阈值，需要后续定向结构化清洗（不是链接可用性问题）。

## 5. 导出结果

已生成发布目录：`release_exports/v4.2`

关键文件：

- `release_exports/v4.2/knowledge_base_import_ready.csv`
- `release_exports/v4.2/import_bundle_report.json`
- `release_exports/v4.2/repair_round_report.json`
- `release_exports/v4.2/relink_official_map_v4_2.csv`
- `release_exports/v4.2/web_seed_urls_v1_2/v2_2/v3_2_*`

导入包总条目：`303`

## 6. 下一步建议

1. 对 `WEBV2-001 / WEBV2-012 / WEBV3-002` 执行“条款级结构化抽取模板”（按 answer/steps/ppe/forbidden/emergency 分栏重写）。
2. 单独给上述 3 条再跑一轮 `audit -> rewrite -> audit -> recheck`，目标至少 `2/3` 进入 recheck pass。
3. 对 `WEBV3-001/003/004/014` 再开一轮补链（V4.3），避免 v3.x 基础池里长期存在 412/blocked。
