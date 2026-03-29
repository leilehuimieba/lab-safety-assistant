from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import validate_eval_dashboard_gate as veg


def make_row(week: str, **metrics: float) -> veg.WeeklyRow:
    base = {
        "safety_refusal_rate": 0.95,
        "emergency_pass_rate": 0.90,
        "qa_pass_rate": 0.85,
        "coverage_rate": 0.80,
        "latency_p95_ms": 3000.0,
        "route_success_rate": 0.95,
        "route_timeout_rate": 0.05,
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


def test_route_gate_detects_consecutive_route_failure() -> None:
    rows = [
        make_row("2026-W11", route_success_rate=0.30, route_timeout_rate=0.60),
        make_row("2026-W12", route_success_rate=0.20, route_timeout_rate=0.70),
    ]
    violations = veg.evaluate_consecutive_week_violations(
        rows,
        targets={**veg.DEFAULT_TARGETS, **veg.ROUTE_TARGETS},
        metrics=["route_success_rate", "route_timeout_rate"],
        weeks=2,
    )
    assert len(violations) == 2
    assert any("route_success_rate" in item for item in violations)
    assert any("route_timeout_rate" in item for item in violations)


def test_override_warn_only_turns_gate_fail_into_pass(tmp_path: Path, monkeypatch) -> None:
    docs_eval = tmp_path / "docs" / "eval"
    docs_eval.mkdir(parents=True, exist_ok=True)
    (docs_eval / "eval_dashboard_gate_enabled.flag").write_text("", encoding="utf-8")
    (docs_eval / "eval_dashboard_data.json").write_text(
        json.dumps(
            {
                "weekly": {
                    "smoke": [
                        {
                            "week": "2026-W11",
                            "run_count": 1,
                            "safety_refusal_rate": 0.99,
                            "emergency_pass_rate": 0.95,
                            "qa_pass_rate": 0.90,
                            "coverage_rate": 0.95,
                            "latency_p95_ms": 1200.0,
                            "route_success_rate": 0.20,
                            "route_timeout_rate": 0.70,
                        },
                        {
                            "week": "2026-W12",
                            "run_count": 1,
                            "safety_refusal_rate": 0.99,
                            "emergency_pass_rate": 0.95,
                            "qa_pass_rate": 0.90,
                            "coverage_rate": 0.95,
                            "latency_p95_ms": 1200.0,
                            "route_success_rate": 0.10,
                            "route_timeout_rate": 0.80,
                        },
                    ]
                },
                "smoke_runs": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (docs_eval / "eval_dashboard_gate_override.json").write_text(
        json.dumps(
            {
                "enabled": True,
                "mode": "warn_only",
                "starts_on": date.today().isoformat(),
                "ends_on": date.today().isoformat(),
                "reason": "temporary route instability",
                "ticket": "OPS-TEST",
                "approver": "tester",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "validate_eval_dashboard_gate.py",
            "--repo-root",
            str(tmp_path),
            "--quiet",
        ],
    )
    assert veg.main() == 0


def test_override_absent_keeps_gate_failure(tmp_path: Path, monkeypatch) -> None:
    docs_eval = tmp_path / "docs" / "eval"
    docs_eval.mkdir(parents=True, exist_ok=True)
    (docs_eval / "eval_dashboard_gate_enabled.flag").write_text("", encoding="utf-8")
    (docs_eval / "eval_dashboard_data.json").write_text(
        json.dumps(
            {
                "weekly": {
                    "smoke": [
                        {
                            "week": "2026-W11",
                            "run_count": 1,
                            "safety_refusal_rate": 0.99,
                            "emergency_pass_rate": 0.95,
                            "qa_pass_rate": 0.90,
                            "coverage_rate": 0.95,
                            "latency_p95_ms": 1200.0,
                            "route_success_rate": 0.20,
                            "route_timeout_rate": 0.70,
                        },
                        {
                            "week": "2026-W12",
                            "run_count": 1,
                            "safety_refusal_rate": 0.99,
                            "emergency_pass_rate": 0.95,
                            "qa_pass_rate": 0.90,
                            "coverage_rate": 0.95,
                            "latency_p95_ms": 1200.0,
                            "route_success_rate": 0.10,
                            "route_timeout_rate": 0.80,
                        },
                    ]
                },
                "smoke_runs": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "validate_eval_dashboard_gate.py",
            "--repo-root",
            str(tmp_path),
            "--quiet",
        ],
    )
    assert veg.main() == 1


def test_gate_failover_enforcement_warns_on_single_fail_status(tmp_path: Path, monkeypatch) -> None:
    docs_eval = tmp_path / "docs" / "eval"
    docs_eval.mkdir(parents=True, exist_ok=True)
    (docs_eval / "eval_dashboard_gate_enabled.flag").write_text("", encoding="utf-8")
    (docs_eval / "eval_dashboard_data.json").write_text(
        json.dumps(
            {
                "weekly": {
                    "smoke": [
                        {
                            "week": "2026-W11",
                            "run_count": 1,
                            "safety_refusal_rate": 0.99,
                            "emergency_pass_rate": 0.95,
                            "qa_pass_rate": 0.90,
                            "coverage_rate": 0.95,
                            "latency_p95_ms": 1200.0,
                            "route_success_rate": 0.90,
                            "route_timeout_rate": 0.05,
                        },
                        {
                            "week": "2026-W12",
                            "run_count": 1,
                            "safety_refusal_rate": 0.99,
                            "emergency_pass_rate": 0.95,
                            "qa_pass_rate": 0.90,
                            "coverage_rate": 0.95,
                            "latency_p95_ms": 1200.0,
                            "route_success_rate": 0.90,
                            "route_timeout_rate": 0.05,
                        },
                    ]
                },
                "smoke_runs": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (docs_eval / "failover_status.json").write_text(
        json.dumps(
            {
                "latest": {
                    "generated_at": "2099-01-01T00:00:00+00:00",
                    "result": "fail",
                },
                "recent_runs": [
                    {"result": "pass"},
                    {"result": "fail"},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "validate_eval_dashboard_gate.py",
            "--repo-root",
            str(tmp_path),
            "--quiet",
            "--enforce-failover-status",
            "--failover-status-json",
            "docs/eval/failover_status.json",
        ],
    )
    # New graded policy: single fail is warning, not immediate block.
    assert veg.main() == 0


def test_gate_failover_enforcement_blocks_on_fail_streak_threshold(tmp_path: Path, monkeypatch) -> None:
    docs_eval = tmp_path / "docs" / "eval"
    docs_eval.mkdir(parents=True, exist_ok=True)
    (docs_eval / "eval_dashboard_gate_enabled.flag").write_text("", encoding="utf-8")
    (docs_eval / "eval_dashboard_data.json").write_text(
        json.dumps(
            {
                "weekly": {
                    "smoke": [
                        {
                            "week": "2026-W11",
                            "run_count": 1,
                            "safety_refusal_rate": 0.99,
                            "emergency_pass_rate": 0.95,
                            "qa_pass_rate": 0.90,
                            "coverage_rate": 0.95,
                            "latency_p95_ms": 1200.0,
                            "route_success_rate": 0.90,
                            "route_timeout_rate": 0.05,
                        },
                        {
                            "week": "2026-W12",
                            "run_count": 1,
                            "safety_refusal_rate": 0.99,
                            "emergency_pass_rate": 0.95,
                            "qa_pass_rate": 0.90,
                            "coverage_rate": 0.95,
                            "latency_p95_ms": 1200.0,
                            "route_success_rate": 0.90,
                            "route_timeout_rate": 0.05,
                        },
                    ]
                },
                "smoke_runs": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (docs_eval / "failover_status.json").write_text(
        json.dumps(
            {
                "latest": {
                    "generated_at": "2099-01-01T00:00:00+00:00",
                    "result": "fail",
                },
                "recent_runs": [
                    {"result": "pass"},
                    {"result": "fail"},
                    {"result": "fail"},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "validate_eval_dashboard_gate.py",
            "--repo-root",
            str(tmp_path),
            "--quiet",
            "--enforce-failover-status",
            "--failover-status-json",
            "docs/eval/failover_status.json",
            "--failover-fail-streak-threshold",
            "2",
        ],
    )
    assert veg.main() == 1


def test_gate_failover_enforcement_pass_with_allow_degraded(tmp_path: Path, monkeypatch) -> None:
    docs_eval = tmp_path / "docs" / "eval"
    docs_eval.mkdir(parents=True, exist_ok=True)
    (docs_eval / "eval_dashboard_gate_enabled.flag").write_text("", encoding="utf-8")
    (docs_eval / "eval_dashboard_data.json").write_text(
        json.dumps(
            {
                "weekly": {
                    "smoke": [
                        {
                            "week": "2026-W11",
                            "run_count": 1,
                            "safety_refusal_rate": 0.99,
                            "emergency_pass_rate": 0.95,
                            "qa_pass_rate": 0.90,
                            "coverage_rate": 0.95,
                            "latency_p95_ms": 1200.0,
                            "route_success_rate": 0.90,
                            "route_timeout_rate": 0.05,
                        },
                        {
                            "week": "2026-W12",
                            "run_count": 1,
                            "safety_refusal_rate": 0.99,
                            "emergency_pass_rate": 0.95,
                            "qa_pass_rate": 0.90,
                            "coverage_rate": 0.95,
                            "latency_p95_ms": 1200.0,
                            "route_success_rate": 0.90,
                            "route_timeout_rate": 0.05,
                        },
                    ]
                },
                "smoke_runs": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (docs_eval / "failover_status.json").write_text(
        json.dumps(
            {
                "latest": {
                    "generated_at": "2099-01-01T00:00:00+00:00",
                    "result": "degraded",
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "validate_eval_dashboard_gate.py",
            "--repo-root",
            str(tmp_path),
            "--quiet",
            "--enforce-failover-status",
            "--failover-allow-degraded",
            "--failover-status-json",
            "docs/eval/failover_status.json",
        ],
    )
    assert veg.main() == 0
