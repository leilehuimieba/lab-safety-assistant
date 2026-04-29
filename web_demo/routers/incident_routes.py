from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..models import IncidentRecord, IncidentCreateRequest, IncidentUpdateRequest
from ..services import load_incident_records, create_incident_record, update_incident_record

router = APIRouter()


@router.get("/api/incidents", response_model=list[IncidentRecord])
def incidents(status: str = "", only_overdue: bool = False) -> list[IncidentRecord]:
    rows = load_incident_records()
    status_value = (status or "").strip().lower()
    if status_value:
        rows = [item for item in rows if item.status.lower() == status_value]
    if only_overdue:
        rows = [item for item in rows if item.overdue]
    return rows


@router.post("/api/incidents", response_model=IncidentRecord)
def create_incident(payload: IncidentCreateRequest) -> IncidentRecord:
    return create_incident_record(payload)


@router.patch("/api/incidents/{incident_id}", response_model=IncidentRecord)
def patch_incident(incident_id: str, payload: IncidentUpdateRequest) -> IncidentRecord:
    return update_incident_record(incident_id, payload)


@router.delete("/api/incidents/{incident_id}")
def delete_incident(incident_id: str) -> dict[str, str]:
    from ..repositories import INCIDENT_REVIEWS_FILE, safe_read_csv_rows
    from libs.common_io import write_csv

    rows = safe_read_csv_rows(INCIDENT_REVIEWS_FILE)
    filtered = [row for row in rows if (row.get("incident_id") or "").strip() != incident_id]
    if len(filtered) == len(rows):
        raise HTTPException(status_code=404, detail="incident not found.")

    if filtered:
        write_csv(INCIDENT_REVIEWS_FILE, filtered, fieldnames=list(rows[0].keys()) if rows else [])
    else:
        INCIDENT_REVIEWS_FILE.write_text("", encoding="utf-8")
    return {"message": "deleted", "incident_id": incident_id}
