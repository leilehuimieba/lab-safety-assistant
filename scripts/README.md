# scripts 目录说明

## 分层结构

1. `pipeline/`：抓取、清洗、入库流水线脚本
2. `release/`：发布打包与导出脚本
3. `qa/`：质量门禁与校验脚本

## 兼容策略

根目录的同名脚本（如 `scripts/web_ingest_pipeline.py`）为兼容入口，
会转发到子目录脚本执行。这样可以保证：

1. 旧命令不变
2. CI 配置不需要立即迁移
3. 文档链接不因重构失效


## 默认项目根目录

- 当前默认项目根目录：`D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github`
- 如无特殊说明，所有 `scripts/*.ps1` 与 `scripts/*.py` 默认都应从该新路径仓库理解和执行。
- 旧 `D:\workspace` 只保留为历史回退点，不再作为默认脚本入口。
