# Lab Safety Assistant — 交接提示词

如果你（AI Agent）接手了本项目，请先阅读此文件以了解当前状态。

---

## 1. 项目基本信息

- **仓库**: `https://github.com/leilehuimieba/lab-safety-assistant`
- **本地路径**: `D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github`
- **分支**: `main`（当前 HEAD: `50da402`）
- **技术栈**: Python 3.13, FastAPI, uvicorn, pytest

---

## 2. 已完成的重构工作

`main` 分支已完成以下模块化重构：

### 服务层拆分
- `web_demo/services/core.py`（1,275 行）→ 10 个 domain service 模块
  - `kb_service.py`, `answer_service.py`, `llm_output_service.py`, `upstream_service.py`, `emergency_service.py`, `meta_service.py`, `risk_service.py`, `training_service.py`, `incident_service.py`, `dashboard_service.py`
- `services/__init__.py` 保留兼容性 re-export

### 路由层拆分
- `web_demo/app.py`（2,318 行）→ 6 个 domain router + 精简 app factory
  - `chat_routes.py`, `risk_routes.py`, `training_routes.py`, `incident_routes.py`, `admin_routes.py`, `dify_proxy.py`
- `routers/__init__.py` 聚合所有 router

### Pipeline 拆分
- `scripts/pipeline/document_ingest_pipeline.py`（1,130→512）+ `pdf_extractor.py`（539）
- `scripts/pipeline/web_ingest_pipeline.py`（826→315）+ `web_fetcher.py`（258）+ `web_content_extractor.py`（230）
- 新建 `libs/ingest_io.py` 共享 IO 工具

### 公共库
- `libs/common_io.py`: CSV/JSONL 读写（替换 11 个脚本中的重复实现）
- `libs/text_utils.py`: 搜索文本规范化（`normalize_search_text`, `extract_tokens`）
- `libs/time_utils.py`: 时间解析（`parse_datetime`, `within_days`）

### 命名规范化
- 4 个同名 `normalize_text` → 分别重命名
  - `normalize_search_text`（text_utils.py）
  - `clean_document_text`（ingest_io.py）
  - `clean_web_text`（web_content_extractor.py）
  - `strip_whitespace_lower`（eval_smoke.py）

---

## 3. 已修复的关键 Bug

### ✅ 启动脚本模块路径错误（已修复）
**问题**: `app.py` 使用相对导入（`from .models import Citation`），但启动脚本调用 `uvicorn.run("app:app", ...)` 会将其作为独立模块导入，导致：
```
ImportError: attempted relative import with no known parent package
```
**修复**: 两个启动脚本均已改为 `uvicorn.run("web_demo.app:app", ...)`，工作目录指向 repo root。

### ✅ Training Roster 功能遗漏（已修复）
**问题**: 重构时 `training_routes.py` 遗漏了 3 个 roster 端点。
**修复**: 已补充模型类（`TrainingRosterItem` 等）和全部端点（`/api/training/roster_status`, `/api/training/roster_upload`, `/api/training/roster_template.csv`）。

### ✅ 测试 monkeypatch 目标错误（已修复）
**问题**: `test_training_roster_status.py` 仍尝试 patch `web_app.TRAINING_ROSTER_FILE`。
**修复**: 改为 patch `web_demo.routers.training_routes` 模块。

---

## 4. 当前项目状态

| 检查项 | 状态 |
|--------|------|
| pytest 全部测试 | ✅ 138/138 通过 |
| `start_web_demo_local.ps1` 启动 | ✅ 实测正常（8088 端口） |
| git status | ✅ 干净 |
| main 分支 | ✅ 已推送（HEAD: `50da402`） |

---

## 5. 如何启动项目

### 本地 Web Demo（推荐）
```powershell
cd lab-safe-assistant-github
powershell -ExecutionPolicy Bypass -File scripts\start_web_demo_local.ps1
```
- 自动检查 `.env.web_demo`，不存在时从模板创建
- 默认端口 `8088`，健康检查: `http://127.0.0.1:8088/health`

### 手动启动（调试）
```powershell
cd lab-safe-assistant-github
$env:DIFY_BASE_URL="http://127.0.0.1:8081"
$env:DIFY_APP_API_KEY="your-key"
python -m uvicorn web_demo.app:app --host 127.0.0.1 --port 8088
```

### 运行测试
```powershell
pytest tests/ -q
```

---

## 6. 已知注意事项

1. **本地 `master` 是孤儿分支**: 已合并到 `main`，如有需要可删除本地 `master` 分支
2. **`.env.web_demo` 包含密钥**: 该文件在 `.gitignore` 中，不会提交
3. **PowerShell 脚本换行符**: `.gitattributes` 配置 `*.ps1 text eol=crlf`，提交时 git 会自动转换
4. **测试 patch 策略**: monkeypatch 必须指向具体模块的导入路径（如 `"web_demo.routers.chat_routes.call_dify_lab"`），不能指向聚合的 `web_demo.app`

---

## 7. 如需继续工作

建议首先运行：
```powershell
pytest tests/ -q          # 确认全部通过
```

如有新增需求或发现问题，先检查：
- `web_demo/routers/` — 新端点放这里
- `web_demo/services/` — 业务逻辑放这里
- `libs/` — 共享工具放这里
- `scripts/pipeline/` — 流水线脚本放这里
