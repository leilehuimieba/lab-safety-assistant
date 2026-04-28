from __future__ import annotations

"""管理仪表盘与工作区状态服务

- load_admin_dashboard: 聚合 checklist、training、low-confidence、incident 多域数据生成仪表盘
- build_workspace_status: 探测 Dify 连通性并汇总知识库与队列状态
- build_weekly_report_markdown: 将仪表盘数据格式化为 Markdown 周报
- export_rows_to_csv: 将数据行导出为 CSV 字符串
- summarize_top_values: 统计字段高频值（支持分隔符拆分）
"""
import csv
import io
import os
from datetime import datetime
from typing import Any

from ..models import (
    AdminDashboardResponse, DashboardHighRiskScenario,
    DashboardLowConfidenceItem, DashboardMetric,
    WorkspaceStatusItem, WorkspaceStatusResponse,
)
from ..repositories import (
    CHECKLIST_RUNS_FILE, DIFY_DEFAULT_BASE_URL, DIFY_DEFAULT_TIMEOUT,
    KB_IMPORT_SUCCESS_COUNT, LOW_CONFIDENCE_QUEUE_FILE,
    TRAINING_ATTEMPTS_FILE,
    safe_read_csv_rows, within_days,
)
from .upstream_service import resolve_dify_api_base
from .incident_service import load_incident_records
from .risk_service import filter_checklist_rows
from .training_service import load_training_stats

def summarize_top_values(rows: list[dict[str, str]], key: str, *, limit: int = 6, splitter: str = ";") -> list[WorkspaceStatusItem]:
    counts: dict[str, int] = {}
    for row in rows:
        raw = str(row.get(key) or "").strip()
        if not raw:
            continue
        if splitter:
            parts = [item.strip() for item in raw.split(splitter) if item.strip()]
        else:
            parts = [raw]
        for part in parts:
            counts[part] = counts.get(part, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]
    return [WorkspaceStatusItem(label=label, count=count) for label, count in ranked]
def build_workspace_status() -> WorkspaceStatusResponse:
    rows = get_kb_entries()
    app_key = os.getenv("DIFY_APP_API_KEY", "").strip()
    timeout = float(os.getenv("DIFY_TIMEOUT", str(DIFY_DEFAULT_TIMEOUT)) or str(DIFY_DEFAULT_TIMEOUT))
    dify_status = "unconfigured"
    if app_key:
        endpoint = f"{resolve_dify_api_base()}/parameters"
        try:
            resp = requests.get(endpoint, headers={"Authorization": f"Bearer {app_key}"}, timeout=(5, 8))
            dify_status = "reachable" if resp.status_code < 400 else f"http_{resp.status_code}"
        except requests.RequestException as exc:
            dify_status = f"unreachable: {exc.__class__.__name__}"

    return WorkspaceStatusResponse(
        dify_enabled=bool(app_key),
        dify_base_url=resolve_dify_api_base(),
        dify_timeout=timeout,
        dify_app_key_configured=bool(app_key),
        dify_connection_status=dify_status,
        kb_rows=len(rows),
        kb_imported=KB_IMPORT_SUCCESS_COUNT,
        low_confidence_queue_count=len(safe_read_csv_rows(LOW_CONFIDENCE_QUEUE_FILE)),
        top_categories=summarize_top_values(rows, "category", limit=6, splitter=""),
        top_hazards=summarize_top_values(rows, "hazard_types", limit=8, splitter=";"),
    )
def export_rows_to_csv(headers: list[str], rows: list[dict[str, Any]]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=headers)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue()
def build_weekly_report_markdown(days: int, risk_level: str, incident_status: str) -> str:
    dashboard = load_admin_dashboard(days=days, risk_level=risk_level, incident_status=incident_status)
    lines = [
        f"# Weekly Safety Report ({datetime.now().strftime('%Y-%m-%d')})",
        "",
        f"- Window: last {days} days",
        f"- Risk filter: {risk_level or 'all'}",
        f"- Incident status filter: {incident_status or 'all'}",
        "",
        "## Key Metrics",
    ]
    for item in dashboard.metrics:
        lines.append(f"- {item.label}: {item.value} ({item.detail})")
    lines.extend(["", "## Low-Confidence TOP"])
    if dashboard.low_confidence_top:
        for item in dashboard.low_confidence_top:
            lines.append(f"- {item.label}: {item.count}")
    else:
        lines.append("- No low-confidence queue items in this window.")
    lines.extend(["", "## Recent High-Risk Scenarios"])
    if dashboard.recent_high_risk_scenarios:
        for item in dashboard.recent_high_risk_scenarios:
            lines.append(
                f"- {item.submitted_at} | {item.risk_level} | {'PASS' if item.allow_start else 'BLOCKED'} | {item.scenario}"
            )
    else:
        lines.append("- No high-risk checklist records in this window.")
    lines.extend(["", "## Incident Summary"])
    for key, value in dashboard.incident_summary.items():
        lines.append(f"- {key}: {value}")
    if dashboard.overdue_incidents:
        lines.extend(["", "## Overdue Incident Reminders"])
        for item in dashboard.overdue_incidents:
            lines.append(f"- {item}")
    return "\n".join(lines) + "\n"
def load_admin_dashboard(days: int = 30, risk_level: str = "", incident_status: str = "") -> AdminDashboardResponse:
    checklist_rows = filter_checklist_rows(safe_read_csv_rows(CHECKLIST_RUNS_FILE), days=days, risk_level=risk_level)
    blocked = sum(1 for row in checklist_rows if (row.get("allow_start") or "").strip().lower() == "false")
    checklist_total = len(checklist_rows)
    checklist_block_rate = (blocked / checklist_total) if checklist_total else 0.0

    training_attempt_rows = [
        row for row in safe_read_csv_rows(TRAINING_ATTEMPTS_FILE) if days <= 0 or within_days(row.get("submitted_at", ""), days)
    ]
    training_stats = load_training_stats()
    if training_attempt_rows:
        scores = [int(float(row.get("score", "0") or "0")) for row in training_attempt_rows]
        passed = sum(1 for row in training_attempt_rows if (row.get("passed") or "").strip().lower() == "true")
        training_stats = training_stats.model_copy(
            update={
                "attempt_count": len(training_attempt_rows),
                "pass_rate": round(passed / len(training_attempt_rows), 4),
                "average_score": round(sum(scores) / len(scores), 2) if scores else 0.0,
                "latest_submitted_at": training_attempt_rows[-1].get("submitted_at", "") or "",
                "recent_scores": scores[-10:],
            }
        )

    low_confidence_counts: dict[str, int] = {}
    for row in safe_read_csv_rows(LOW_CONFIDENCE_QUEUE_FILE):
        if days > 0 and not within_days(row.get("created_at", ""), days):
            continue
        label = (row.get("low_confidence_reason") or row.get("question") or "unknown").strip() or "unknown"
        low_confidence_counts[label] = low_confidence_counts.get(label, 0) + 1

    high_risk_rows: list[DashboardHighRiskScenario] = []
    for row in checklist_rows:
        score = int(float(row.get("risk_score", "0") or "0"))
        if score < 4:
            continue
        high_risk_rows.append(
            DashboardHighRiskScenario(
                submitted_at=(row.get("submitted_at") or "").strip(),
                scenario=(row.get("scenario") or "").strip(),
                risk_level=(row.get("risk_level") or "").strip(),
                allow_start=(row.get("allow_start") or "").strip().lower() == "true",
                operator=(row.get("operator") or "").strip(),
            )
        )
    high_risk_rows.sort(key=lambda item: item.submitted_at, reverse=True)

    incidents = [
        item
        for item in load_incident_records()
        if (days <= 0 or within_days(item.reported_at, days))
        and ((incident_status or "").strip().lower() in {"", item.status.lower()})
    ]
    incident_summary = {
        "open": sum(1 for item in incidents if item.status == "open"),
        "in_review": sum(1 for item in incidents if item.status == "in_review"),
        "action_in_progress": sum(1 for item in incidents if item.status == "action_in_progress"),
        "verified": sum(1 for item in incidents if item.status == "verified"),
        "closed": sum(1 for item in incidents if item.status == "closed"),
    }

    metrics = [
        DashboardMetric(
            label="清单阻断率",
            value=f"{round(checklist_block_rate * 100)}%",
            detail=f"{blocked}/{checklist_total or 0} 次提交被阻断",
        ),
        DashboardMetric(
            label="培训通过率",
            value=f"{round(training_stats.pass_rate * 100)}%",
            detail=f"{training_stats.attempt_count} 次作答",
        ),
        DashboardMetric(
            label="培训平均分",
            value=f"{training_stats.average_score}",
            detail="基于已完成的考核记录",
        ),
        DashboardMetric(
            label="未闭环复盘数",
            value=str(incident_summary["open"] + incident_summary["in_review"] + incident_summary["action_in_progress"]),
            detail="待处理 + 复盘中 + 整改中",
        ),
        DashboardMetric(
            label="逾期整改数",
            value=str(sum(1 for item in incidents if item.overdue)),
            detail="已超期且尚未复核/闭环",
        ),
    ]
    low_confidence_top = [
        DashboardLowConfidenceItem(label=label, count=count)
        for label, count in sorted(low_confidence_counts.items(), key=lambda item: item[1], reverse=True)[:5]
    ]
    return AdminDashboardResponse(
        metrics=metrics,
        low_confidence_top=low_confidence_top,
        recent_high_risk_scenarios=high_risk_rows[:5],
        incident_summary=incident_summary,
        overdue_incidents=[
            f"{item.incident_id} | {item.title} | overdue {item.overdue_days} day(s)"
            for item in incidents
            if item.overdue
        ][:5],
    )
