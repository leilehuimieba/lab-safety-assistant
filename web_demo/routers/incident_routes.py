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
