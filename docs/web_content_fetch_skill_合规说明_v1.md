# Web Content Fetch Skill 合规说明（v1）

## 1. 目的

本项目新增的 `web-content-fetcher` Skill 仅用于实验数据采集与研究验证，服务于：

- 实验室安全知识库构建
- 链接内容提取质量评测
- 检索与问答准确率优化

## 2. 合规边界

允许场景：

- 抓取公开可访问页面
- 采集实验所需最小文本片段
- 保留来源链接用于可追溯验证

禁止场景：

- 绕过登录、付费墙、访问控制
- 违反目标网站服务条款的大规模抓取
- 将原文整篇二次分发为公开数据库

## 3. 处理原则

1. 先提取，再总结，禁止在未提取成功时生成“猜测性总结”。
2. 识别登录墙时必须返回 `requires_auth=true`，并给出失败原因。
3. 保存 `url/provider/fetched_at` 便于审计与复核。
4. 对低质量提取结果进入人工复核流程，不直接入库。

## 4. 仓库位置

- Skill 目录：`skills/web-content-fetcher/`
- 关键脚本：`skills/web-content-fetcher/scripts/fetch_web_content.py`
- Pipeline 包装脚本：`skills/web-content-fetcher/scripts/run_web_ingest_pipeline.py`
- 路由策略：`skills/web-content-fetcher/references/provider_routing.md`
- Skill 内合规文件：`skills/web-content-fetcher/references/compliance_scope.md`

已接入主流水线：

- `scripts/web_ingest_pipeline.py --fetcher-mode auto|skill|legacy`

## 5. 团队执行要求

- 每周至少一次抽样检查提取结果准确性与来源合法性。
- 若发现来源限制策略变化，及时更新路由或改为人工采集。
- 对外展示时仅展示“摘要 + 来源链接”，不直接复制大量原文。
