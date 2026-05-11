# Verify — 重构前端导入

## 验证范围
1. 新前端源码完整复制到项目目录 `web_demo/frontend/`
2. 构建产物（`dist/`）可正常生成，路径使用相对路径 `./assets/...`
3. FastAPI 后端能正确服务静态文件（JS/CSS）并返回正确 MIME 类型
4. SPA 路由回退正常工作（非 API/非 assets 路径返回 `index.html`）
5. API 兼容层覆盖新前端所有调用端点
6. 关键 API 返回 HTTP 200

## 验证方法
- 本地启动 `uvicorn web_demo.app:app --host 127.0.0.1 --port 8090`
- HTTP 请求验证（PowerShell `Invoke-WebRequest`）
- 浏览器访问验证（Playwright，受限于 Windows 环境暂部分阻塞）

## 预期结果
- `GET /` → 返回新前端 `index.html`（~708 bytes）
- `GET /assets/main-*.js` → `Content-Type: application/javascript`
- `GET /assets/main-*.css` → `Content-Type: text/css`
- `GET /api/emergency/cards` → 200
- `GET /api/training/questions` → 200
- `GET /api/admin/dashboard` → 200
- `GET /api/incidents` → 200
- `POST /api/risk/assess` → 200（取决于本地知识库加载速度）
- `POST /api/emergency/match` → 200

## 实际结果

### HTTP 层验证（全部通过，2026-04-28 21:50）
- `GET /` → 200，返回新前端 `index.html`（396 bytes）✅
- `GET /assets/main-*.js` → 200，`Content-Type: application/javascript`（61 KB）✅
- `GET /assets/main-*.css` → 200，`Content-Type: text/css`（30 KB）✅
- `GET /api/emergency/cards` → 200 ✅
- `GET /api/training/questions` → 200 ✅
- `GET /api/admin/dashboard` → 200 ✅
- `GET /api/incidents` → 200 ✅
- `POST /api/risk/assess` → 200，响应时间 < 1s ✅（已修复 embedding 加载超时）
- `POST /api/emergency/match` → 200 ✅
- `POST /api/chat` → 200 ✅

### SPA 路由回退验证（全部通过）
以下 8 个客户端路由均正确返回 `index.html`，由前端接管渲染：
- `/` → 200 HTML ✅
- `/checklist` → 200 HTML ✅
- `/emergency` → 200 HTML ✅
- `/training` → 200 HTML ✅
- `/teacher` → 200 HTML ✅
- `/admin` → 200 HTML ✅
- `/incidents` → 200 HTML ✅
- `/status` → 200 HTML ✅

### 本轮补充验证（2026-05-11）
- `npm run build` 重新构建通过 ✅
- `tests/test_web_demo_api_smoke.py`、`tests/test_web_demo_logic.py`、`tests/test_web_demo_risk_assess.py` 通过 ✅
- `GET /api/workspace/status` 由 500 修复为 200 ✅
- 前端导航递归与侧边栏高亮问题已修复，并完成重新构建 ✅
- 前端首页 in-app browser 卡死问题已修复；`waitUntil: "domcontentloaded"` 可稳定通过 ✅
- Playwright 浏览器自动化验证通过：桌面端与移动端均可打开首页并切换到 `/status` ✅
- 已生成验证截图：`docs/product/_tmp_homepage_after_fix.png`、`docs/product/_tmp_status_desktop.png`、`docs/product/_tmp_status_mobile.png` ✅
- 新增系统设计、数据库设计、API 规范、实施与测试补充文档 ✅

## 已修复问题

### 1. Risk Assess API 超时
- **根因**：`retrieve_citations` 默认启用 `sentence-transformers` embedding 语义检索，首次加载 BAAI/bge-m3 模型耗时极长（>30s）
- **修复**：`web_demo/app.py` 中添加 `os.environ.setdefault("ENABLE_EMBEDDING", "0")`，默认禁用 embedding，fallback 到纯文本检索（响应时间 < 0.1s）

### 2. 后端 500 错误（导入过程中发现）
- `web_demo/services/risk_service.py` 缺少 `within_days` 导入 → 已补充
- `web_demo/services/training_service.py` 缺少 `TRAINING_ATTEMPTS_FILE` / `TRAINING_MISTAKES_FILE` 导入 → 已补充
- `web_demo/services/incident_service.py` 缺少 `INCIDENT_REVIEWS_FILE` 导入 → 已补充

### 3. Windows 静态文件 MIME 类型
- **根因**：Windows 下 Python `mimetypes` 模块未正确识别 `.js` 为 `application/javascript`
- **修复**：`web_demo/app.py` 中自定义 `/assets/{path:path}` 路由，强制根据扩展名返回正确 MIME 类型

### 4. 外部字体依赖
- **根因**：`index.html` 引用 Google Fonts，中国大陆网络环境下可能导致浏览器加载阻塞
- **修复**：移除 Google Fonts 链接，改用系统字体栈（`system-ui, -apple-system, Segoe UI, PingFang SC, Microsoft YaHei` 等）

### 5. 当前轮修复（2026-05-11）
- **前端导航递归触发**：`router.ts` 中监听 `navigate` 后再次调用 `navigateTo()` 会造成重复触发，已删除重复监听。
- **侧边栏高亮失效**：`Sidebar.ts` 未设置 `data-route`，导致 `main.ts` 的激活态同步失效，已补齐。
- **首页无响应 / 浏览器卡死**：`AppShell.ts` 中通过 `MutationObserver` 监听 `sidebar.class` 再反向修改类名，在嵌入式浏览器环境中会导致初始化阶段阻塞；现已改为由 `main.ts` 显式调用 `__syncLayoutState` 同步侧边栏与遮罩状态。
- **工作区状态接口 500**：`dashboard_service.py` 缺少 `requests` 与 `get_kb_entries` 导入，已补齐并恢复 200。
- **系统状态页字段不一致**：`SystemStatus.ts` 仍按旧 `name/version/description` 读取元信息，已改为对齐 `/api/meta` 的真实响应字段。
- **补充文档落地**：已新增系统设计、数据库设计、API 规范、实施与测试补充文档，作为后续答辩与实现对齐依据。

## 证据位置
- 新前端源码：`web_demo/frontend/src/`
- 新前端构建产物：`web_demo/frontend/dist/`
- 后端适配：`web_demo/app.py`、`web_demo/routers/*.py`、`web_demo/models.py`
- 旧前端备份：`web_demo/templates/index.html.bak_v82`
- 截图尝试：`output/frontend_verify_home.png`
- 本轮验证截图：`docs/product/_tmp_homepage_after_fix.png`、`docs/product/_tmp_status_desktop.png`、`docs/product/_tmp_status_mobile.png`

## 环境准备
`.venv312` 虚拟环境已安装核心依赖：
```powershell
cd D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github
.\.venv312\Scripts\python -m pip install -r requirements.txt
```
注：首次安装需约 2-3 分钟，sentence-transformers 等可选依赖可跳过。

## 本地复现步骤
```powershell
cd D:\newwork\lab-safe-assistant-workspace\lab-safe-assistant-github
$env:ENABLE_EMBEDDING="0"
.\.venv312\Scripts\python -m uvicorn web_demo.app:app --host 127.0.0.1 --port 8090
# 浏览器访问 http://127.0.0.1:8090
```

## 剩余建议
- 当前首页与系统状态页已通过自动化验证；下一轮建议补齐 `/checklist`、`/teacher`、`/admin` 三条高价值演示链路截图
- 如需重新启用 embedding 语义检索，设置环境变量 `ENABLE_EMBEDDING=1` 并确保模型已预下载
