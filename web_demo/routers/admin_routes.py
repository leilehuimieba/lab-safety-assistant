from __future__ import annotations

import os
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse, Response

from ..models import AdminDashboardResponse, WorkspaceStatusResponse
from ..repositories import (
    CHECKLIST_RUNS_FILE, TRAINING_ATTEMPTS_FILE, TRAINING_MISTAKES_FILE,
    LOW_CONFIDENCE_QUEUE_FILE, INCIDENT_REVIEWS_FILE,
    QUEUE_HEADERS, CHECKLIST_HEADERS, TRAINING_ATTEMPT_HEADERS,
    safe_read_csv_rows, within_days,
)
from ..services import (
    load_incident_records, load_admin_dashboard, filter_checklist_rows,
    build_workspace_status, build_weekly_report_markdown, export_rows_to_csv,
)

router = APIRouter()


@router.get("/api/admin/dashboard", response_model=AdminDashboardResponse)
def admin_dashboard(days: int = 30, risk_level: str = "", incident_status: str = "") -> AdminDashboardResponse:
    return load_admin_dashboard(days=days, risk_level=risk_level, incident_status=incident_status)


@router.get("/api/admin/export.csv")
def admin_export_csv(scope: str = "checklists", days: int = 30, risk_level: str = "", incident_status: str = "") -> Response:
    return _admin_export_csv(scope, days, risk_level, incident_status)


def _admin_export_csv(scope: str, days: int, risk_level: str, incident_status: str) -> Response:
    scope_value = (scope or "").strip().lower()
    if scope_value == "checklists":
        rows = filter_checklist_rows(safe_read_csv_rows(CHECKLIST_RUNS_FILE), days=days, risk_level=risk_level)
        headers = CHECKLIST_HEADERS
    elif scope_value == "training":
        rows = [row for row in safe_read_csv_rows(TRAINING_ATTEMPTS_FILE) if days <= 0 or within_days(row.get("submitted_at", ""), days)]
        headers = TRAINING_ATTEMPT_HEADERS
    elif scope_value == "low_confidence":
        rows = [row for row in safe_read_csv_rows(LOW_CONFIDENCE_QUEUE_FILE) if days <= 0 or within_days(row.get("created_at", ""), days)]
        headers = QUEUE_HEADERS
    elif scope_value == "incidents":
        incident_rows = [
            item for item in load_incident_records()
            if (days <= 0 or within_days(item.reported_at, days))
            and ((incident_status or "").strip().lower() in {"", item.status.lower()})
        ]
        rows = [
            {
                "incident_id": item.incident_id,
                "reported_at": item.reported_at,
                "updated_at": item.updated_at,
                "reporter": item.reporter,
                "title": item.title,
                "scenario": item.scenario,
                "severity": item.severity,
                "status": item.status,
                "location": item.location,
                "cause_categories": " | ".join(item.cause_categories),
                "immediate_actions": " | ".join(item.immediate_actions),
                "corrective_actions": " | ".join(item.corrective_actions),
                "owner": item.owner,
                "due_date": item.due_date,
                "closure_notes": item.closure_notes,
                "recurrence_risk": item.recurrence_risk,
                "overdue": str(item.overdue).lower(),
                "overdue_days": item.overdue_days,
            }
            for item in incident_rows
        ]
        headers = INCIDENT_HEADERS + ["recurrence_risk", "overdue", "overdue_days"]
    else:
        raise HTTPException(status_code=400, detail="unsupported export scope.")

    csv_text = export_rows_to_csv(headers, rows)
    filename = f"{scope_value}_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/api/admin/weekly_report.md")
def admin_weekly_report(days: int = 7, risk_level: str = "", incident_status: str = "") -> PlainTextResponse:
    return _admin_weekly_report(days, risk_level, incident_status)


def _admin_weekly_report(days: int, risk_level: str, incident_status: str) -> PlainTextResponse:
    markdown = build_weekly_report_markdown(days=days, risk_level=risk_level, incident_status=incident_status)
    return PlainTextResponse(
        content=markdown,
        headers={"Content-Disposition": f'attachment; filename="weekly_report_{datetime.now().strftime("%Y%m%d")}.md"'},
    )


@router.get("/api/admin/export")
def admin_export(scope: str = "checklists", days: int = 30, risk_level: str = "", incident_status: str = "") -> Response:
    return _admin_export_csv(scope, days, risk_level, incident_status)


@router.get("/api/admin/weekly-report")
def admin_weekly_report_alias(days: int = 7, risk_level: str = "", incident_status: str = "") -> PlainTextResponse:
    return _admin_weekly_report(days, risk_level, incident_status)


@router.get("/api/workspace/status", response_model=WorkspaceStatusResponse)
def workspace_status() -> WorkspaceStatusResponse:
    return build_workspace_status()
