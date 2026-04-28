from __future__ import annotations

import csv
import io
import os
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..models import (
    TrainingSessionResponse, TrainingSubmitRequest, TrainingSubmitResponse, TrainingStatsResponse,
    TrainingRosterItem, TrainingRosterStatusResponse, TrainingRosterUploadRequest, TrainingRosterUploadResponse,
)
from ..repositories import DEFAULT_TRAINING_PASS_THRESHOLD
from ..services import get_training_questions, to_public_question, grade_training_submit, load_training_stats
from libs.common_io import read_csv as _read_csv, write_csv as _write_csv

router = APIRouter()

TRAINING_ATTEMPTS_FILE = Path("artifacts/training/training_attempts.csv")
TRAINING_ROSTER_FILE = Path("artifacts/training/training_roster.csv")
TRAINING_ROSTER_TEMPLATE_FILE = Path("data_sources/training_roster_template.csv")
TRAINING_ROSTER_HEADERS = ["student_id", "name", "class_name", "lab_group", "required_training"]


def _truthy_csv_value(value: str) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "y", "是", "需要"}


def _load_training_roster_rows() -> list[dict[str, str]]:
    rows = _read_csv(TRAINING_ROSTER_FILE)
    if rows:
        return rows
    return _read_csv(TRAINING_ROSTER_TEMPLATE_FILE)


def _normalize_training_roster_csv(csv_text: str) -> list[dict[str, str]]:
    buffer = io.StringIO(csv_text.lstrip("\ufeff"))
    reader = csv.DictReader(buffer)
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV 缺少表头。")

    normalized_headers = {name.strip().lower(): name for name in reader.fieldnames if name}
    if "name" not in normalized_headers and "student_id" not in normalized_headers:
        raise HTTPException(status_code=400, detail="CSV 至少需要 name 或 student_id 列。")

    rows: list[dict[str, str]] = []
    for raw in reader:
        row = {key: (raw.get(normalized_headers.get(key, ""), "") or "").strip() for key in TRAINING_ROSTER_HEADERS}
        if not row["student_id"] and not row["name"]:
            continue
        if not row["required_training"]:
            row["required_training"] = "true"
        rows.append(row)

    if not rows:
        raise HTTPException(status_code=400, detail="CSV 没有有效学生记录。")
    return rows


def _save_training_roster_csv(csv_text: str) -> TrainingRosterUploadResponse:
    rows = _normalize_training_roster_csv(csv_text)
    _write_csv(TRAINING_ROSTER_FILE, rows, fieldnames=TRAINING_ROSTER_HEADERS)
    return TrainingRosterUploadResponse(
        message=f"已导入 {len(rows)} 名学生名单。",
        saved_count=len(rows),
        status=_load_training_roster_status(),
    )


def _load_training_roster_status() -> TrainingRosterStatusResponse:
    roster_rows = [row for row in _load_training_roster_rows() if _truthy_csv_value(row.get("required_training", "true"))]
    attempts = _read_csv(TRAINING_ATTEMPTS_FILE)
    latest_by_key: dict[str, dict[str, str]] = {}

    for row in attempts:
        participant = (row.get("participant") or "").strip()
        if not participant:
            continue
        keys = {participant.lower()}
        submitted_at = row.get("submitted_at", "") or ""
        for key in keys:
            current = latest_by_key.get(key)
            if current is None or submitted_at >= (current.get("submitted_at", "") or ""):
                latest_by_key[key] = row

    items: list[TrainingRosterItem] = []
    for row in roster_rows:
        student_id = (row.get("student_id") or "").strip()
        name = (row.get("name") or row.get("student_name") or student_id or "未命名学生").strip()
        keys = [key.lower() for key in (student_id, name) if key]
        latest = next((latest_by_key[key] for key in keys if key in latest_by_key), None)
        completed = latest is not None
        passed = bool(latest and (latest.get("passed") or "").strip().lower() == "true")
        latest_score = int(float((latest or {}).get("score", "0") or "0")) if latest else 0
        items.append(
            TrainingRosterItem(
                student_id=student_id,
                name=name,
                class_name=(row.get("class_name") or "").strip(),
                lab_group=(row.get("lab_group") or "").strip(),
                completed=completed,
                passed=passed,
                latest_score=latest_score,
                latest_submitted_at=(latest or {}).get("submitted_at", "") or "",
            )
        )

    incomplete = [item for item in items if not item.passed]
    incomplete.sort(key=lambda item: (item.latest_submitted_at or "", item.name), reverse=True)
    return TrainingRosterStatusResponse(
        total_required=len(items),
        completed_count=sum(1 for item in items if item.completed),
        passed_count=sum(1 for item in items if item.passed),
        incomplete_count=len(incomplete),
        incomplete_students=incomplete[:10],
    )


@router.get("/api/training/questions", response_model=TrainingSessionResponse)
def training_questions(limit: int = 5) -> TrainingSessionResponse:
    questions = get_training_questions(limit)
    if not questions:
        raise HTTPException(status_code=500, detail="training bank is empty.")
    session_id = f"SESSION-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:6]}"
    pass_threshold = int(os.getenv("TRAINING_PASS_THRESHOLD", str(DEFAULT_TRAINING_PASS_THRESHOLD)) or "80")
    return TrainingSessionResponse(
        session_id=session_id,
        total_questions=len(questions),
        pass_threshold=pass_threshold,
        questions=[to_public_question(item) for item in questions],
    )


@router.post("/api/training/submit", response_model=TrainingSubmitResponse)
def training_submit(payload: TrainingSubmitRequest) -> TrainingSubmitResponse:
    if not payload.answers:
        raise HTTPException(status_code=400, detail="answers are required.")
    return grade_training_submit(payload)


@router.get("/api/training/stats", response_model=TrainingStatsResponse)
def training_stats() -> TrainingStatsResponse:
    return load_training_stats()


@router.get("/api/training/roster_status", response_model=TrainingRosterStatusResponse)
def training_roster_status() -> TrainingRosterStatusResponse:
    return _load_training_roster_status()


@router.post("/api/training/roster_upload", response_model=TrainingRosterUploadResponse)
def training_roster_upload(payload: TrainingRosterUploadRequest) -> TrainingRosterUploadResponse:
    return _save_training_roster_csv(payload.csv_text)


@router.get("/api/training/roster_template.csv")
def training_roster_template() -> FileResponse:
    if not TRAINING_ROSTER_TEMPLATE_FILE.exists():
        raise HTTPException(status_code=404, detail="training roster template not found")
    return FileResponse(
        TRAINING_ROSTER_TEMPLATE_FILE,
        media_type="text/csv; charset=utf-8",
        filename="training_roster_template.csv",
    )
