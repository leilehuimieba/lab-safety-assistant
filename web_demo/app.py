from __future__ import annotations

from fastapi import FastAPI

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

# 供测试检测 PyYAML 是否安装
try:
    import yaml
except ImportError:
    yaml = None
