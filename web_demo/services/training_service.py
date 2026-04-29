from __future__ import annotations

"""培训题库与考核评分服务

- to_public_question / get_training_questions: 加载并格式化培训题库
- grade_training_submit: 评分并记录培训作答结果（含错题归档）
- load_training_stats: 汇总培训尝试次数、通过率、平均分等统计指标
"""
import json
import os
import random
from datetime import datetime
from typing import Any
from uuid import uuid4

from fastapi import HTTPException

from ..models import (
    TrainingQuestionPublic, TrainingReviewItem,
    TrainingStatsResponse, TrainingSubmitRequest, TrainingSubmitResponse,
)
from ..repositories import (
    DEFAULT_TRAINING_PASS_THRESHOLD,
    TRAINING_ATTEMPT_HEADERS, TRAINING_ATTEMPTS_FILE, TRAINING_MISTAKE_HEADERS, TRAINING_MISTAKES_FILE,
    get_training_bank, safe_read_csv_rows, write_csv_row,
)

def to_public_question(raw: dict[str, Any]) -> TrainingQuestionPublic:
    return TrainingQuestionPublic(
        id=str(raw.get("id") or ""),
        category=str(raw.get("category") or ""),
        prompt=str(raw.get("prompt") or ""),
        options=[str(item) for item in raw.get("options") or []],
        multiple=bool(raw.get("multiple")),
        references=[str(item) for item in raw.get("references") or []],
    )
def get_training_questions(limit: int) -> list[dict[str, Any]]:
    bank = get_training_bank()
    if not bank:
        return []
    limit = max(1, min(limit, len(bank)))
    return random.sample(bank, limit)
def grade_training_submit(payload: TrainingSubmitRequest) -> TrainingSubmitResponse:
    bank = {str(item.get("id") or ""): item for item in get_training_bank()}
    if not bank:
        raise HTTPException(status_code=500, detail="training bank is empty.")

    submitted_at = datetime.now().isoformat(timespec="seconds")
    attempt_id = f"TRN-{datetime.now().strftime('%Y%m%d')}-{uuid4().hex[:8]}"
    answers_by_id = {item.question_id: sorted(set(item.selected_indices)) for item in payload.answers}

    review: list[TrainingReviewItem] = []
    wrong_categories: list[str] = []
    correct_count = 0

    for question_id, selected in answers_by_id.items():
        raw = bank.get(question_id)
        if not raw:
            continue
        correct_indices = sorted(int(idx) for idx in raw.get("correct_indices") or [])
        is_correct = selected == correct_indices
        if is_correct:
            correct_count += 1
        else:
            wrong_categories.append(str(raw.get("category") or "Uncategorized"))
            write_csv_row(
                TRAINING_MISTAKES_FILE,
                TRAINING_MISTAKE_HEADERS,
                {
                    "attempt_id": attempt_id,
                    "submitted_at": submitted_at,
                    "participant": payload.participant.strip() or "anonymous",
                    "session_id": payload.session_id,
                    "question_id": question_id,
                    "category": str(raw.get("category") or ""),
                    "prompt": str(raw.get("prompt") or ""),
                    "selected_indices": json.dumps(selected, ensure_ascii=False),
                    "correct_indices": json.dumps(correct_indices, ensure_ascii=False),
                    "references": " | ".join(str(item) for item in raw.get("references") or []),
                },
            )
        review.append(
            TrainingReviewItem(
                question_id=question_id,
                category=str(raw.get("category") or ""),
                prompt=str(raw.get("prompt") or ""),
                selected_indices=selected,
                correct_indices=correct_indices,
                correct=is_correct,
                explanation=str(raw.get("explanation") or ""),
                references=[str(item) for item in raw.get("references") or []],
            )
        )

    total_questions = len(review)
    score = int(round((correct_count / total_questions) * 100)) if total_questions else 0
    pass_threshold = int(os.getenv("TRAINING_PASS_THRESHOLD", str(DEFAULT_TRAINING_PASS_THRESHOLD)) or "80")
    passed = score >= pass_threshold
    weak_categories = sorted(set(wrong_categories))

    write_csv_row(
        TRAINING_ATTEMPTS_FILE,
        TRAINING_ATTEMPT_HEADERS,
        {
            "attempt_id": attempt_id,
            "submitted_at": submitted_at,
            "participant": payload.participant.strip() or "anonymous",
            "session_id": payload.session_id,
            "score": score,
            "total_questions": total_questions,
            "pass_threshold": pass_threshold,
            "passed": str(passed).lower(),
            "weak_categories": " | ".join(weak_categories),
        },
    )

    recommended_actions = (
        ["Training passed. Review the explanations once and continue to scenario drills."]
        if passed
        else [
            "Review all incorrect questions and linked references.",
            "Repeat the quiz after updating weak categories.",
            "Do not approve independent high-risk work until the pass threshold is met.",
        ]
    )
    return TrainingSubmitResponse(
        attempt_id=attempt_id,
        session_id=payload.session_id,
        participant=payload.participant,
        submitted_at=submitted_at,
        score=score,
        total_questions=total_questions,
        pass_threshold=pass_threshold,
        passed=passed,
        weak_categories=weak_categories,
        recommended_actions=recommended_actions,
        review=review,
    )
def load_training_stats() -> TrainingStatsResponse:
    attempts: list[dict[str, str]] = []
    mistakes: dict[str, int] = {}
    latest_submitted_at = ""

    attempts = safe_read_csv_rows(TRAINING_ATTEMPTS_FILE)
    for row in safe_read_csv_rows(TRAINING_MISTAKES_FILE):
        category = (row.get("category") or "Uncategorized").strip() or "Uncategorized"
        mistakes[category] = mistakes.get(category, 0) + 1

    scores = [int(float(row.get("score", "0") or "0")) for row in attempts]
    passed_count = sum(1 for row in attempts if (row.get("passed") or "").strip().lower() == "true")
    if attempts:
        latest_submitted_at = attempts[-1].get("submitted_at", "") or ""

    return TrainingStatsResponse(
        attempt_count=len(attempts),
        pass_rate=round((passed_count / len(attempts)) if attempts else 0.0, 4),
        average_score=round((sum(scores) / len(scores)) if scores else 0.0, 2),
        latest_submitted_at=latest_submitted_at,
        category_mistakes=dict(sorted(mistakes.items(), key=lambda item: item[1], reverse=True)[:5]),
        recent_scores=scores[-10:],
    )
