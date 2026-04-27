# LabSafe Assistant 模块化重构 — 交接文档

> 生成时间：2026-04-27
> 重构范围：`lab-safe-assistant-github` 项目

---

## 一、背景与目标

本项目是一个"实验室安全小助手"课程演示系统，核心架构为：
- **web_demo/**：FastAPI 单体 Web 服务（原 2318 行 `app.py`）
- **scripts/**：80+ 个独立命令行脚本（数据流水线、发布管理、质量门禁）
- **local_env/dify/**：本地 Dify 知识库部署

本次重构目标：解决 `app.py` 过于庞大、scripts 重复代码多、无包化结构等工程化短板。

---

## 二、已完成工作

### 2.1 统一依赖管理
- 创建根目录 `requirements.txt`，合并 web_demo / scripts 的分散依赖
- 子目录 `requirements.txt` 保留但标注为"已由根目录统一管理"

### 2.2 提取公共库 `libs/`
- `libs/common_io.py`：`now_iso()`、`read_csv_rows()`、`write_csv()`、`load_json()`、`save_json()`
- `libs/project_paths.py`：`REPO_ROOT`、`SCRIPTS_DIR`、`ARTIFACTS_DIR` 等常量
- **已落地**：21 个 scripts 的 `now_iso()` 已替换为 `from libs.common_io import now_iso`

### 2.3 Python 包化
- `scripts/`、`scripts/pipeline/`、`scripts/release/`、`scripts/qa/` 添加 `__init__.py`
- `web_demo/` 添加 `__init__.py`
- 测试配置 `pytest.ini` 增加 `pythonpath = .`，支持标准包导入

### 2.4 `web_demo` 服务层拆分（核心成果）

`app.py` 已完成两轮拆分：先拆为 6 个 domain router，再将 `services/core.py` 拆为 10 个 domain service。

**Router 层** (`web_demo/routers/`)：
| 文件 | 职责 | 行数 |
|------|------|------|
| `chat_routes.py` | 问答、应急卡片、搜索 | ~168 |
| `risk_routes.py` | 风险评估、检查清单 | ~36 |
| `training_routes.py` | 培训题库与考核 | ~42 |
| `incident_routes.py` | 事故记录 CRUD | ~29 |
| `admin_routes.py` | 管理看板、导出、周报 | ~94 |
| `dify_proxy.py` | Dify API 代理 | ~25 |

**Service 层** (`web_demo/services/`)：
| 文件 | 职责 | 行数 |
|------|------|------|
| `kb_service.py` | 知识库检索与规则匹配 | ~119 |
| `answer_service.py` | 答案构建与低置信度处理 | ~157 |
| `llm_output_service.py` | LLM 输出清洗与乱码修复 | ~35 |
| `upstream_service.py` | Dify 与 OpenAI 兼容上游调用 | ~228 |
| `emergency_service.py` | 应急卡片匹配 | ~45 |
| `meta_service.py` | 应用元信息 | ~30 |
| `risk_service.py` | 风险评估与检查清单 | ~179 |
| `training_service.py` | 培训题库与考核评分 | ~154 |
| `incident_service.py` | 事故记录管理 | ~201 |
| `dashboard_service.py` | 管理仪表盘与工作区状态 | ~206 |

- `services/__init__.py` 作为兼容层重新导出全部符号，已有测试无需改动

### 2.5 文档同步更新
- `local_env/dify/README.md`：记录 Dify 访问地址（8081）和管理员账号
- 10+ 个文档/配置中的 `localhost:8080` → `localhost:8081`
- `.env` 中 `EXPOSE_NGINX_PORT=8080` → `8081`

---

## 三、当前项目状态

### 测试状态
```
pytest tests/  →  100% 通过（约 90 个测试）
```

### 关键账号（本地 Dify）
| 项目 | 值 |
|------|-----|
| 访问地址 | `http://localhost:8081/signin` |
| 邮箱 | `3337153688@qq.com` |
| 密码 | `a123456789` |

### 关键路径
```
项目根目录：D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github
Dify 部署：local_env/dify/docker/
Web 服务：web_demo/
公共库：libs/
测试：tests/
```

---

## 四、遗留问题 / 下一步方向

### P1（建议优先）
1. **脚本层 `scripts/pipeline/` 大文件拆分**
   - `document_ingest_pipeline.py`（原 1,130 行）已拆出 `pdf_extractor.py` + `libs/ingest_io.py`
   - `web_ingest_pipeline.py`（原 826 行）已拆出 `web_fetcher.py` + `web_content_extractor.py`
   - `unified_kb_pipeline.py`（367 行）若继续膨胀可考虑拆为 `kb_merge.py` + `kb_validate.py`

2. **逐个替换 scripts/ 的 `read_csv` / `write_csv` / `load_json`**
   - 各脚本签名差异较大（返回 tuple vs list、参数顺序不同），**不适合批量自动化**，需逐个手工处理
   - 已替换 `now_iso()` 作为示范

### P2
3. **引入 DAO 抽象层**
   - 当前 `repositories.py` 直接操作 CSV，可抽象 `BaseRepository` 接口，未来换数据库无痛

4. **清理 scripts/ 根层双轨制兼容入口**
   - 根层脚本转发到 `scripts/pipeline/`、`scripts/release/` 等子目录，可考虑统一移除转发层

---

## 五、新对话提示词（直接复制给 AI）

```markdown
你是一个资深的 Python 后端工程师，正在继续维护 `lab-safe-assistant-github` 项目（实验室安全小助手）。

**上下文（来自上一次重构交接）**：
- 项目已完成两轮模块化重构，核心成果：
  - `web_demo/app.py` 从 2318 行拆分为 6 个 domain router + 10 个 domain service
  - `scripts/pipeline/document_ingest_pipeline.py` 拆出 `pdf_extractor.py` + `libs/ingest_io.py`
  - `scripts/pipeline/web_ingest_pipeline.py` 拆出 `web_fetcher.py` + `web_content_extractor.py`
  - 创建了 `libs/common_io.py`、`libs/project_paths.py`、`libs/ingest_io.py` 作为公共库
  - 21 个 scripts 已替换为 `from libs.common_io import now_iso`
  - 全部测试通过（pytest tests/ → 100%）
- 本地 Dify 地址：`http://localhost:8081/signin`，账号 `3337153688@qq.com`，密码 `a123456789`
- 项目根目录：`D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github`

**你的任务**：
（请用户在此处填写具体任务，如"继续拆分 services/core.py"、"替换 scripts 中的 read_csv/write_csv"、"引入 DAO 抽象层"等）

**约束**：
1. 每次修改后必须运行 `pytest tests/ -q` 验证测试全部通过
2. 遵循现有代码风格（无类型注解要求，函数名 snake_case）
3. 最小改动原则，不要修改未涉及的逻辑
4. 优先使用 `libs/common_io` 和 `libs/project_paths`，避免新增重复代码
```

---

## 六、注意事项

1. **不要删除 `app.py.bak`**：保留在 `web_demo/app.py.bak`，用于回溯对比
2. **`web_demo/services/` 各模块使用 `..models` 和 `..repositories` 相对导入**：因为文件位于 `web_demo/services/` 子包内
3. **scripts/ 测试仍需 `sys.path` 兼容**：`tests/conftest.py` 保留了 `scripts/` 的 `sys.path.insert`，因为大量测试直接 `import quality_gate` 而非 `from scripts import quality_gate`
4. **Docker / Dify 端口**：本地 Dify nginx 映射到宿主机的 **8081**（因 80 被系统占用）
