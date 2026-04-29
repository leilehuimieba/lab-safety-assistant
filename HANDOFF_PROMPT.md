# Lab Safety Assistant — 交接提示词

如果你（AI Agent）接手了本项目，请先阅读此文件以了解当前状态。

---

## 1. 项目基本信息

- **仓库**: `https://github.com/leilehuimieba/lab-safety-assistant`
- **本地路径**: `D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github`
- **分支**: `main`
- **技术栈**: Python 3.13, FastAPI, uvicorn, pytest
- **pytest**: **138/138 通过**

---

## 2. 本对话已完成的核心工作

### 2.1 本地 bge-m3 语义检索集成

**目标**: 为 Web Demo 知识库检索引入向量语义检索，解决纯文本 token 匹配对同义词/语义变体召回能力弱的问题。

**实现方式**:
- **双后端 Embedding 引擎** (`libs/embedding_utils.py`):
  - `sentence-transformers` 后端：从 HuggingFace 加载 `BAAI/bge-m3`
  - `ollama` 后端：调用本地 Ollama `/api/embed` API（**当前使用**）
  - 通过 `EMBEDDING_BACKEND` 环境变量切换
  - 支持多数据集独立索引（`_index_states` 字典），知识库和应急卡片各自有独立缓存
- **混合检索** (`web_demo/services/kb_service.py`):
  - `retrieve_citations` 现在 = 文本 token 匹配 + bge-m3 语义检索
  - 默认语义权重 **12.0**（经 5 组关键问题对比测试后确定）
  - `SEMANTIC_WEIGHT` 支持环境变量调整
  - `ENABLE_EMBEDDING` 支持动态开关（`0` 关闭，回退纯文本）
- **评估工具** (`scripts/eval_kb_retrieval.py`):
  - 对比纯文本 vs 混合检索的召回差异
  - 支持 `--semantic-weight` 参数调参

**当前运行状态**:
- Ollama 服务需**单独运行**（`ollama serve`）
- bge-m3 模型已安装在 Ollama 中（`ollama list` 可见，1.2GB）
- 知识库索引已构建：`.cache/embedding/`（1,149 条）
- 应急卡片索引已构建：`.cache/embedding_emergency/`（4 条）

### 2.2 语义检索扩展到应急卡片

- **改造** `web_demo/services/emergency_service.py`:
  - `match_emergency_card` 从纯关键词匹配升级为 **bge-m3 语义 + 文本 token 混合匹配**
  - 默认语义权重 `EMERGENCY_SEMANTIC_WEIGHT=6.0`
- 验证结果（中文查询 → 正确匹配）:
  - "眼睛被酸溅到了" → `chemical_splash`
  - "实验室着火了" → `lab_fire`
  - "有人触电了" → `electric_shock`
  - "化学品泄漏了" → `chemical_leak`

### 2.3 测试环境兼容性修复

- `tests/conftest.py`: 默认设置 `ENABLE_EMBEDDING=0`，避免 CI 中自动下载 HuggingFace 模型导致超时

### 2.4 Docker 产品化封装

- `Dockerfile`: 多阶段构建（`python:3.13-slim`）
- `docker-compose.yml`: 一键启动，含健康检查、Volume 挂载（logs/artifacts/.cache）
- `.dockerignore`: 排除开发/测试/日志文件
- `.github/workflows/build-and-push-image.yml`: CI/CD 自动构建多架构镜像（amd64/arm64），推送到 `ghcr.io`
- `docs/ops/docker_deploy_guide.md`: 完整 Docker 部署文档

---

## 3. 当前项目状态

| 检查项 | 状态 |
|--------|------|
| pytest 全部测试 | ✅ 138/138 通过 |
| 本地 Web Demo 启动 | ✅ 8088 端口正常 |
| Ollama bge-m3 可用 | ✅ 已安装 |
| 知识库语义索引 | ✅ 已构建 |
| 应急卡片语义索引 | ✅ 已构建 |
| Docker 封装 | ✅ 已完成 |
| git status | 待提交（新增/修改文件见下方） |

### 本对话新增/修改的文件清单

```
新增:
  libs/embedding_utils.py
  scripts/eval_kb_retrieval.py
  Dockerfile
  docker-compose.yml
  .dockerignore
  .github/workflows/build-and-push-image.yml
  docs/ops/docker_deploy_guide.md

修改:
  web_demo/services/kb_service.py          (混合检索)
  web_demo/services/emergency_service.py   (语义匹配)
  tests/conftest.py                        (ENABLE_EMBEDDING=0)
  requirements.txt                         (+sentence-transformers, +numpy)
  HANDOFF_PROMPT.md                        (本文件)
```

---

## 4. 关键配置速查

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `EMBEDDING_BACKEND` | `sentence-transformers` | `ollama` 或 `sentence-transformers` |
| `EMBEDDING_MODEL` | `BAAI/bge-m3` | HuggingFace 模型名 / Ollama 模型名 |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API 地址 |
| `ENABLE_EMBEDDING` | `1` | `0` 关闭语义检索（纯文本 fallback） |
| `SEMANTIC_WEIGHT` | `12.0` | 知识库语义权重 |
| `EMERGENCY_SEMANTIC_WEIGHT` | `6.0` | 应急卡片语义权重 |

### 启动项目

```powershell
# 方式一：Windows 本地开发
powershell -ExecutionPolicy Bypass -File scripts\start_web_demo_local.ps1

# 方式二：Docker 一键启动
cp deploy/.env.web_demo.example .env.web_demo
# 编辑 .env.web_demo 填入 DIFY_APP_API_KEY
docker compose up -d

# 方式三：手动调试
python -m uvicorn web_demo.app:app --host 127.0.0.1 --port 8088
```

### 运行测试

```powershell
pytest tests/ -q
```

---

## 5. 已知注意事项

1. **Ollama 必须单独运行**: 语义检索依赖本地 Ollama 服务，`ollama serve` 需保持运行。如果 Ollama 未启动，语义检索自动 fallback（不会崩溃，但退化为纯文本检索）。
2. **`.env.web_demo` 包含密钥**: 该文件在 `.gitignore` 中，不会提交。
3. **首次构建索引较慢**: 首次调用 `retrieve_citations` 或 `match_emergency_card` 时，会自动为知识库/应急卡片计算 embedding（约 10~30 秒，取决于 Ollama 响应速度）。后续启动秒级加载。
4. **Docker 中访问宿主机 Ollama**: 容器内默认通过 `http://host.docker.internal:11434` 访问宿主机 Ollama。Linux Docker 需额外配置 `--add-host=host.docker.internal:host-gateway`。
5. **sentence-transformers 作为备选**: 已加入 `requirements.txt`，但默认不启用。如需切换为 HuggingFace backend，设置 `EMBEDDING_BACKEND=sentence-transformers`，首次会自动下载 bge-m3（约 1.2GB）。

---

## 6. 如需继续工作

建议首先运行：
```powershell
pytest tests/ -q          # 确认全部通过
```

### 可选的下一步方向

1. **构建并验证 Docker 镜像**: `docker build -t lab-safe-assistant:latest .`
2. **配置 Nginx HTTPS 反向代理**: 基于 `deploy/nginx/` 已有模板
3. **编写 Helm Chart / K8s 配置**: 云原生部署
4. **全链路检索评估**: 运行 `python scripts/eval_kb_retrieval.py --output reports/retrieval_compare.csv`
5. **接入 Rerank 模型**: 在语义检索后增加 `bge-reranker` 精排层
6. **Pipeline 向量化**: 让文档/网页摄取流程在分块后自动生成 embedding
7. **其他功能开发**: 培训推荐、事故分析、仪表盘优化等
