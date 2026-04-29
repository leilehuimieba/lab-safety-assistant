from __future__ import annotations

import mimetypes
import os

# 默认禁用 embedding 语义检索，避免模型加载导致演示超时
# 如需启用，在环境变量中设置 ENABLE_EMBEDDING=1
os.environ.setdefault("ENABLE_EMBEDDING", "0")

mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .models import Citation
from .routers import (
    chat_router,
    emergency_router,
    incident_router,
    meta_router,
    risk_router,
    training_router,
    admin_router,
)
from .services import (
    retrieve_citations, match_rule, should_enforce_terminal_rule,
    build_rule_answer, assess_low_confidence, append_low_confidence_followup,
    build_fallback_lab_answer, build_risk_assessment,
    build_checklist_template, evaluate_checklist_submission,
    to_emergency_card, match_emergency_card,
    get_training_questions, to_public_question, grade_training_submit,
    load_training_stats, load_admin_dashboard, filter_checklist_rows,
    load_incident_records, create_incident_record, update_incident_record,
    build_workspace_status, build_weekly_report_markdown, export_rows_to_csv,
    resolve_dify_api_base, build_dify_proxy_auth, sanitize_llm_output,
    call_dify_lab,
)

app = FastAPI(title="LabSafe Assistant Web Demo")

app.include_router(meta_router)
app.include_router(chat_router)
app.include_router(risk_router)
app.include_router(emergency_router)
app.include_router(training_router)
app.include_router(incident_router)
app.include_router(admin_router)

from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent
_ASSETS_DIR = _BASE_DIR / "frontend" / "dist" / "assets"

# 自定义静态资源路由（强制正确 MIME 类型，避免 Windows mimetypes 问题）
@app.get("/assets/{path:path}")
def serve_asset(path: str):
    file_path = _ASSETS_DIR / path
    if not file_path.exists():
        raise HTTPException(status_code=404)
    ext = file_path.suffix.lower()
    media_type = {
        ".js": "application/javascript",
        ".mjs": "application/javascript",
        ".css": "text/css",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".svg": "image/svg+xml",
        ".woff2": "font/woff2",
        ".woff": "font/woff",
        ".ttf": "font/ttf",
        ".json": "application/json",
    }.get(ext, "application/octet-stream")
    return FileResponse(
        str(file_path),
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=3600"},
    )


# SPA catch-all：所有非 API、非 assets 路径返回前端 index.html
@app.get("/{path:path}")
def spa_fallback(path: str):
    if path.startswith(("api/", "assets/")):
        raise HTTPException(status_code=404)
    return FileResponse(str(_BASE_DIR / "frontend" / "dist" / "index.html"))


# 供测试检测 PyYAML 是否安装
try:
    import yaml
except ImportError:
    yaml = None
