from __future__ import annotations

import validate_eval_dashboard_gate as veg


def make_row(week: str, **metrics: float) -> veg.WeeklyRow:
    base = {
        "safety_refusal_rate": 0.95,
        "emergency_pass_rate": 0.90,
        "qa_pass_rate": 0.85,
        "coverage_rate": 0.80,
        "latency_p95_ms": 3000.0,
    }
    base.update(metrics)
    return veg.WeeklyRow(week=week, run_count=1, metrics=base)


def test_gate_no_violation_when_less_than_required_weeks() -> None:
    rows = [make_row("2026-W12", qa_pass_rate=0.1)]
    violations = veg.evaluate_consecutive_week_violations(
        rows,
        targets=veg.DEFAULT_TARGETS,
        metrics=["qa_pass_rate"],
        weeks=2,
    )
    assert violations == []


def test_gate_detects_two_week_consecutive_failure() -> None:
    rows = [
        make_row("2026-W11", qa_pass_rate=0.40),
        make_row("2026-W12", qa_pass_rate=0.30),
    ]
    violations = veg.evaluate_consecutive_week_violations(
        rows,
        targets=veg.DEFAULT_TARGETS,
        metrics=["qa_pass_rate"],
        weeks=2,
    )
    assert len(violations) == 1
    assert "qa_pass_rate" in violations[0]


def test_gate_passes_if_second_week_recovers() -> None:
    rows = [
        make_row("2026-W11", coverage_rate=0.60),
        make_row("2026-W12", coverage_rate=0.82),
    ]
    violations = veg.evaluate_consecutive_week_violations(
        rows,
        targets=veg.DEFAULT_TARGETS,
        metrics=["coverage_rate"],
        weeks=2,
    )
    assert violations == []
