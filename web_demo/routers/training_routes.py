from __future__ import annotations

import os
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from ..models import (
    TrainingSessionResponse, TrainingSubmitRequest, TrainingSubmitResponse, TrainingStatsResponse,
)
from ..repositories import DEFAULT_TRAINING_PASS_THRESHOLD
from ..services import get_training_questions, to_public_question, grade_training_submit, load_training_stats

router = APIRouter()


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
