from __future__ import annotations

import generate_web_prefetch_status as gwps


def test_normalize_status_marks_403_as_blocked() -> None:
    status = gwps.normalize_status(
        fetch_status="ok",
        status="success",
        error="",
        status_code=403,
        quality_score=0.0,
    )
    assert status == "blocked"


def test_normalize_status_marks_404_as_not_found() -> None:
    status = gwps.normalize_status(
        fetch_status="ok",
        status="success",
        error="",
        status_code=404,
        quality_score=0.0,
    )
    assert status == "not_found"


def test_normalize_status_keeps_real_success_as_ok() -> None:
    status = gwps.normalize_status(
        fetch_status="ok",
        status="success",
        error="",
        status_code=200,
        quality_score=0.72,
    )
    assert status == "ok"

