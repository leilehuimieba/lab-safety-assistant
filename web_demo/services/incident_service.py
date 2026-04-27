from __future__ import annotations

"""事故记录管理服务

- load_incident_records / create_incident_record / update_incident_record: 事故 CRUD
- compute_incident_due_state / compute_incident_recurrence_risk: 逾期与复发风险计算
- parse_json_list_field / write_incident_records: 辅助工具与批量写入
"""
import csv
import json
from datetime import datetime
from typing import Any

from fastapi import HTTPException

from ..models import IncidentCreateRequest, IncidentRecord, IncidentUpdateRequest
from ..repositories import (
    INCIDENT_HEADERS, INCIDENT_STATUS_ORDER,
    parse_datetime, safe_read_csv_rows,
    _INCIDENT_LOCK,
)

def parse_json_list_field(value: str) -> list[str]:
    text = (value or "").strip()
    if not text:
        return []
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return [item.strip() for item in re.split(r"[|;]", text) if item.strip()]
    if isinstance(payload, list):
        return [str(item).strip() for item in payload if str(item).strip()]
    return [str(payload).strip()]
def compute_incident_recurrence_risk(
    *,
    severity: str,
    cause_categories: list[str],
    all_records: list[IncidentRecord],
    current_id: str,
) -> str:
    score = {"low": 1, "medium": 2, "high": 3, "critical": 4}.get(severity, 2)
    normalized_causes = {item.strip().lower() for item in cause_categories if item.strip()}
    for item in all_records:
        if item.incident_id == current_id:
            continue
        other_causes = {entry.strip().lower() for entry in item.cause_categories if entry.strip()}
        overlap = len(normalized_causes & other_causes)
        if overlap:
            score += 1
        if item.severity in {"high", "critical"} and overlap:
            score += 1
    if len(normalized_causes) >= 3:
        score += 1
    if score <= 2:
        return "low"
    if score == 3:
        return "medium"
    if score == 4:
        return "high"
    return "critical"
def compute_incident_due_state(due_date: str, status: str) -> tuple[bool, int]:
    if status in {"verified", "closed"}:
        return False, 0
    due = parse_datetime(due_date)
    if due is None:
        return False, 0
    overdue_days = (datetime.now().date() - due.date()).days
    return overdue_days > 0, max(overdue_days, 0)
def load_incident_records() -> list[IncidentRecord]:
    records = [
        IncidentRecord(
            incident_id=(row.get("incident_id") or "").strip(),
            reported_at=(row.get("reported_at") or "").strip(),
            updated_at=(row.get("updated_at") or "").strip(),
            reporter=(row.get("reporter") or "").strip(),
            title=(row.get("title") or "").strip(),
            scenario=(row.get("scenario") or "").strip(),
            severity=(row.get("severity") or "").strip(),
            status=(row.get("status") or "").strip(),
            location=(row.get("location") or "").strip(),
            cause_categories=parse_json_list_field(row.get("cause_categories") or ""),
            immediate_actions=parse_json_list_field(row.get("immediate_actions") or ""),
            corrective_actions=parse_json_list_field(row.get("corrective_actions") or ""),
            owner=(row.get("owner") or "").strip(),
            due_date=(row.get("due_date") or "").strip(),
            closure_notes=(row.get("closure_notes") or "").strip(),
        )
        for row in safe_read_csv_rows(INCIDENT_REVIEWS_FILE)
    ]
    enriched: list[IncidentRecord] = []
    for item in records:
        overdue, overdue_days = compute_incident_due_state(item.due_date, item.status)
        enriched.append(
            item.model_copy(
                update={
                    "recurrence_risk": compute_incident_recurrence_risk(
                        severity=item.severity,
                        cause_categories=item.cause_categories,
                        all_records=records,
                        current_id=item.incident_id,
                    ),
                    "overdue": overdue,
                    "overdue_days": overdue_days,
                }
            )
        )
    records = enriched
    records.sort(
        key=lambda item: (
            0 if item.overdue else 1,
            INCIDENT_STATUS_ORDER.get(item.status, 99),
            item.reported_at or "",
        )
    )
    return records
def write_incident_records(records: list[IncidentRecord]) -> None:
    INCIDENT_REVIEWS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with INCIDENT_REVIEWS_FILE.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=INCIDENT_HEADERS)
        writer.writeheader()
        for item in records:
            writer.writerow(
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
                    "cause_categories": json.dumps(item.cause_categories, ensure_ascii=False),
                    "immediate_actions": json.dumps(item.immediate_actions, ensure_ascii=False),
                    "corrective_actions": json.dumps(item.corrective_actions, ensure_ascii=False),
                    "owner": item.owner,
                    "due_date": item.due_date,
                    "closure_notes": item.closure_notes,
                }
            )
def create_incident_record(payload: IncidentCreateRequest) -> IncidentRecord:
    now = datetime.now().isoformat(timespec="seconds")
    incident = IncidentRecord(
        incident_id=f"INC-{datetime.now().strftime('%Y%m%d')}-{uuid4().hex[:8]}",
        reported_at=now,
        updated_at=now,
        reporter=payload.reporter.strip() or "anonymous",
        title=payload.title.strip(),
        scenario=payload.scenario.strip(),
        severity=payload.severity,
        status="open",
        location=payload.location.strip(),
        cause_categories=[item.strip() for item in payload.cause_categories if item.strip()],
        immediate_actions=[item.strip() for item in payload.immediate_actions if item.strip()],
        corrective_actions=[item.strip() for item in payload.corrective_actions if item.strip()],
        owner=payload.owner.strip(),
        due_date=payload.due_date.strip(),
        closure_notes="",
    )
    with _INCIDENT_LOCK:
        records = load_incident_records()
        records.insert(0, incident)
        write_incident_records(records)
        enriched = incident.model_copy(
            update={
                "recurrence_risk": compute_incident_recurrence_risk(
                    severity=incident.severity,
                    cause_categories=incident.cause_categories,
                    all_records=records,
                    current_id=incident.incident_id,
                ),
                "overdue": compute_incident_due_state(incident.due_date, incident.status)[0],
                "overdue_days": compute_incident_due_state(incident.due_date, incident.status)[1],
            }
        )
    return enriched
def update_incident_record(incident_id: str, payload: IncidentUpdateRequest) -> IncidentRecord:
    with _INCIDENT_LOCK:
        records = load_incident_records()
        for idx, item in enumerate(records):
            if item.incident_id != incident_id:
                continue
            updated = item.model_copy(
                update={
                    "updated_at": datetime.now().isoformat(timespec="seconds"),
                    "status": payload.status,
                    "corrective_actions": [entry.strip() for entry in payload.corrective_actions if entry.strip()] or item.corrective_actions,
                    "owner": payload.owner.strip() or item.owner,
                    "due_date": payload.due_date.strip() or item.due_date,
                    "closure_notes": payload.closure_notes.strip() or item.closure_notes,
                }
            )
            records[idx] = updated
            write_incident_records(records)
            enriched = updated.model_copy(
                update={
                    "recurrence_risk": compute_incident_recurrence_risk(
                        severity=updated.severity,
                        cause_categories=updated.cause_categories,
                        all_records=records,
                        current_id=updated.incident_id,
                    ),
                    "overdue": compute_incident_due_state(updated.due_date, updated.status)[0],
                    "overdue_days": compute_incident_due_state(updated.due_date, updated.status)[1],
                }
            )
            return enriched
    raise HTTPException(status_code=404, detail="incident not found.")
