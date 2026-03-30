from __future__ import annotations

import json
import sys
from pathlib import Path

import validate_release_policy as vrp


def _write_policy(path: Path) -> None:
    payload = {
        "version": "v5",
        "profiles": {
            "demo": {
                "allowed_gate_decisions": ["PASS", "WARN", "WARN_ONLY"],
                "max_violation_count": 2,
                "max_warning_count": 6,
                "allowed_override_modes": ["warn_only"],
                "freshness": {
                    "max_risk_note_age_hours": 9999,
                    "max_failover_status_age_hours": 9999,
                },
                "route": {"min_route_success_rate": 0.0, "max_route_timeout_rate": 1.0},
                "latency": {"max_latency_p95_ms": 120000},
                "metrics": {
                    "emergency_pass_rate": {"min": 0.8},
                    "coverage_rate": {"min": 0.75},
                },
                "failover": {
                    "allowed_latest_results": ["pass", "degraded", "fail"],
                    "max_latest_timeout_error_ratio": 1.0,
                    "max_fail_window": 20,
                    "max_fail_streak": 20,
                },
            },
            "prod": {
                "allowed_gate_decisions": ["PASS", "WARN"],
                "max_violation_count": 0,
                "max_warning_count": 2,
                "allowed_override_modes": [],
                "freshness": {
                    "max_risk_note_age_hours": 9999,
                    "max_failover_status_age_hours": 9999,
                },
                "route": {"min_route_success_rate": 0.8, "max_route_timeout_rate": 0.2},
                "latency": {"max_latency_p95_ms": 30000},
                "metrics": {
                    "emergency_pass_rate": {"min": 0.9},
                    "coverage_rate": {"min": 0.85},
                    "qa_pass_rate": {"min": 0.85},
                },
                "failover": {
                    "allowed_latest_results": ["pass", "degraded"],
                    "max_latest_timeout_error_ratio": 0.4,
                    "max_fail_window": 1,
                    "max_fail_streak": 1,
                },
            },
        },
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _write_risk(path: Path, gate_decision: str, violations: list[str], warnings: list[str], *, override: bool = False) -> None:
    payload = {
        "generated_at": "2099-01-01T00:00:00+00:00",
        "gate_decision": gate_decision,
        "violations": violations,
        "warnings": warnings,
        "override_active": override,
        "override_mode": "warn_only" if override else "",
        "latest_route_stats": {
            "route_success_rate": 0.9,
            "route_timeout_rate": 0.1,
        },
        "latest_metrics": {
            "safety_refusal_rate": 1.0,
            "emergency_pass_rate": 0.95,
            "qa_pass_rate": 0.9,
            "coverage_rate": 0.9,
            "latency_p95_ms": 1000.0,
        },
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _write_failover(path: Path, latest_result: str, *, fail_window: int = 0, streak: int = 0) -> None:
    recent_runs = []
    if streak > 0:
        recent_runs.extend([{"result": "pass"}])
        recent_runs.extend([{"result": "fail"} for _ in range(streak)])
    payload = {
        "generated_at": "2099-01-01T00:00:00+00:00",
        "window_counts": {"fail": fail_window},
        "latest": {
            "result": latest_result,
            "timeout_error_ratio": 0.0,
        },
        "recent_runs": recent_runs,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_validate_release_policy_demo_pass(tmp_path: Path, monkeypatch) -> None:
    docs_eval = tmp_path / "docs" / "eval"
    docs_eval.mkdir(parents=True, exist_ok=True)
    _write_policy(docs_eval / "release_policy_v5.json")
    _write_risk(docs_eval / "release_risk_note_auto.json", "WARN_ONLY", ["v1"], [], override=True)
    _write_failover(docs_eval / "failover_status.json", "fail", fail_window=2, streak=2)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "validate_release_policy.py",
            "--repo-root",
            str(tmp_path),
            "--policy-json",
            "docs/eval/release_policy_v5.json",
            "--profile",
            "demo",
            "--risk-note-json",
            "docs/eval/release_risk_note_auto.json",
            "--failover-status-json",
            "docs/eval/failover_status.json",
            "--quiet",
        ],
    )
    assert vrp.main() == 0


def test_validate_release_policy_prod_blocks_warn_only(tmp_path: Path, monkeypatch) -> None:
    docs_eval = tmp_path / "docs" / "eval"
    docs_eval.mkdir(parents=True, exist_ok=True)
    _write_policy(docs_eval / "release_policy_v5.json")
    _write_risk(docs_eval / "release_risk_note_auto.json", "WARN_ONLY", [], [], override=True)
    _write_failover(docs_eval / "failover_status.json", "pass", fail_window=0, streak=0)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "validate_release_policy.py",
            "--repo-root",
            str(tmp_path),
            "--policy-json",
            "docs/eval/release_policy_v5.json",
            "--profile",
            "prod",
            "--risk-note-json",
            "docs/eval/release_risk_note_auto.json",
            "--failover-status-json",
            "docs/eval/failover_status.json",
            "--quiet",
        ],
    )
    assert vrp.main() == 1


def test_validate_release_policy_prod_blocks_fail_streak(tmp_path: Path, monkeypatch) -> None:
    docs_eval = tmp_path / "docs" / "eval"
    docs_eval.mkdir(parents=True, exist_ok=True)
    _write_policy(docs_eval / "release_policy_v5.json")
    _write_risk(docs_eval / "release_risk_note_auto.json", "PASS", [], [])
    _write_failover(docs_eval / "failover_status.json", "degraded", fail_window=0, streak=2)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "validate_release_policy.py",
            "--repo-root",
            str(tmp_path),
            "--policy-json",
            "docs/eval/release_policy_v5.json",
            "--profile",
            "prod",
            "--risk-note-json",
            "docs/eval/release_risk_note_auto.json",
            "--failover-status-json",
            "docs/eval/failover_status.json",
            "--quiet",
        ],
    )
    assert vrp.main() == 1


def test_validate_release_policy_prod_blocks_metric_threshold(tmp_path: Path, monkeypatch) -> None:
    docs_eval = tmp_path / "docs" / "eval"
    docs_eval.mkdir(parents=True, exist_ok=True)
    _write_policy(docs_eval / "release_policy_v5.json")
    _write_risk(docs_eval / "release_risk_note_auto.json", "PASS", [], [])
    risk = json.loads((docs_eval / "release_risk_note_auto.json").read_text(encoding="utf-8"))
    risk["latest_metrics"]["emergency_pass_rate"] = 0.72
    (docs_eval / "release_risk_note_auto.json").write_text(json.dumps(risk, ensure_ascii=False), encoding="utf-8")
    _write_failover(docs_eval / "failover_status.json", "pass", fail_window=0, streak=0)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "validate_release_policy.py",
            "--repo-root",
            str(tmp_path),
            "--policy-json",
            "docs/eval/release_policy_v5.json",
            "--profile",
            "prod",
            "--risk-note-json",
            "docs/eval/release_risk_note_auto.json",
            "--failover-status-json",
            "docs/eval/failover_status.json",
            "--quiet",
        ],
    )
    assert vrp.main() == 1


def test_validate_release_policy_missing_inputs_non_strict_warn_pass(tmp_path: Path, monkeypatch) -> None:
    docs_eval = tmp_path / "docs" / "eval"
    docs_eval.mkdir(parents=True, exist_ok=True)
    _write_policy(docs_eval / "release_policy_v5.json")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "validate_release_policy.py",
            "--repo-root",
            str(tmp_path),
            "--policy-json",
            "docs/eval/release_policy_v5.json",
            "--profile",
            "demo",
            "--risk-note-json",
            "docs/eval/release_risk_note_auto.json",
            "--failover-status-json",
            "docs/eval/failover_status.json",
            "--quiet",
        ],
    )
    assert vrp.main() == 0


def test_validate_release_policy_missing_inputs_strict_fail(tmp_path: Path, monkeypatch) -> None:
    docs_eval = tmp_path / "docs" / "eval"
    docs_eval.mkdir(parents=True, exist_ok=True)
    _write_policy(docs_eval / "release_policy_v5.json")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "validate_release_policy.py",
            "--repo-root",
            str(tmp_path),
            "--policy-json",
            "docs/eval/release_policy_v5.json",
            "--profile",
            "demo",
            "--risk-note-json",
            "docs/eval/release_risk_note_auto.json",
            "--failover-status-json",
            "docs/eval/failover_status.json",
            "--strict",
            "--quiet",
        ],
    )
    assert vrp.main() == 1
