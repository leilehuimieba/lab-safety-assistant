from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import generate_release_risk_note as grn


def write_dashboard(path: Path) -> None:
    payload = {
        "weekly": {
            "smoke": [
                {
                    "week": "2026-W11",
                    "run_count": 1,
                    "safety_refusal_rate": 0.98,
                    "emergency_pass_rate": 0.91,
                    "qa_pass_rate": 0.88,
                    "coverage_rate": 0.93,
                    "latency_p95_ms": 1800.0,
                    "route_success_rate": 0.30,
                    "route_timeout_rate": 0.60,
                },
                {
                    "week": "2026-W12",
                    "run_count": 1,
                    "safety_refusal_rate": 0.98,
                    "emergency_pass_rate": 0.91,
                    "qa_pass_rate": 0.88,
                    "coverage_rate": 0.93,
                    "latency_p95_ms": 1800.0,
                    "route_success_rate": 0.20,
                    "route_timeout_rate": 0.70,
                },
            ]
        },
        "smoke_runs": [
            {
                "run_id": "run_20260328_000000",
                "generated_at": "2026-03-28T00:00:00+08:00",
                "metrics": {
                    "safety_refusal_rate": 0.98,
                    "emergency_pass_rate": 0.91,
                    "qa_pass_rate": 0.88,
                    "coverage_rate": 0.93,
                },
                "route_stats": {
                    "route_success_rate": 0.20,
                    "route_timeout_rate": 0.70,
                },
                "targets": {
                    "safety_refusal_rate": 0.95,
                    "emergency_pass_rate": 0.90,
                    "qa_pass_rate": 0.85,
                    "coverage_rate": 0.80,
                    "latency_p95_ms": 5000.0,
                    "route_success_rate": 0.70,
                    "route_timeout_rate": 0.30,
                },
            }
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def write_dashboard_healthy(path: Path) -> None:
    payload = {
        "weekly": {
            "smoke": [
                {
                    "week": "2026-W11",
                    "run_count": 1,
                    "safety_refusal_rate": 0.98,
                    "emergency_pass_rate": 0.93,
                    "qa_pass_rate": 0.90,
                    "coverage_rate": 0.94,
                    "latency_p95_ms": 1800.0,
                    "route_success_rate": 0.90,
                    "route_timeout_rate": 0.05,
                },
                {
                    "week": "2026-W12",
                    "run_count": 1,
                    "safety_refusal_rate": 0.98,
                    "emergency_pass_rate": 0.93,
                    "qa_pass_rate": 0.90,
                    "coverage_rate": 0.94,
                    "latency_p95_ms": 1800.0,
                    "route_success_rate": 0.90,
                    "route_timeout_rate": 0.05,
                },
            ]
        },
        "smoke_runs": [
            {
                "run_id": "run_20260328_000000",
                "generated_at": "2026-03-28T00:00:00+08:00",
                "metrics": {
                    "safety_refusal_rate": 0.98,
                    "emergency_pass_rate": 0.93,
                    "qa_pass_rate": 0.90,
                    "coverage_rate": 0.94,
                },
                "route_stats": {
                    "route_success_rate": 0.90,
                    "route_timeout_rate": 0.05,
                },
                "targets": {
                    "safety_refusal_rate": 0.95,
                    "emergency_pass_rate": 0.90,
                    "qa_pass_rate": 0.85,
                    "coverage_rate": 0.80,
                    "latency_p95_ms": 5000.0,
                    "route_success_rate": 0.70,
                    "route_timeout_rate": 0.30,
                },
            }
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_generate_release_risk_note_block(tmp_path: Path, monkeypatch) -> None:
    docs_eval = tmp_path / "docs" / "eval"
    docs_eval.mkdir(parents=True, exist_ok=True)
    write_dashboard(docs_eval / "eval_dashboard_data.json")

    monkeypatch.setattr(
        sys,
        "argv",
        ["generate_release_risk_note.py", "--repo-root", str(tmp_path)],
    )
    assert grn.main() == 0

    payload = json.loads((docs_eval / "release_risk_note_auto.json").read_text(encoding="utf-8"))
    assert payload["gate_decision"] == "BLOCK"
    assert payload["violations"]


def test_generate_release_risk_note_warn_only(tmp_path: Path, monkeypatch) -> None:
    docs_eval = tmp_path / "docs" / "eval"
    docs_eval.mkdir(parents=True, exist_ok=True)
    write_dashboard(docs_eval / "eval_dashboard_data.json")
    (docs_eval / "eval_dashboard_gate_override.json").write_text(
        json.dumps(
            {
                "enabled": True,
                "mode": "warn_only",
                "starts_on": date.today().isoformat(),
                "ends_on": date.today().isoformat(),
                "reason": "temporary issue",
                "ticket": "OPS-TEST",
                "approver": "qa-owner",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        ["generate_release_risk_note.py", "--repo-root", str(tmp_path)],
    )
    assert grn.main() == 0
    payload = json.loads((docs_eval / "release_risk_note_auto.json").read_text(encoding="utf-8"))
    assert payload["gate_decision"] == "WARN_ONLY"
    assert payload["override_active"] is True


def test_generate_release_risk_note_warn_on_failover_warning(tmp_path: Path, monkeypatch) -> None:
    docs_eval = tmp_path / "docs" / "eval"
    docs_eval.mkdir(parents=True, exist_ok=True)
    write_dashboard_healthy(docs_eval / "eval_dashboard_data.json")
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
                "window_counts": {"pass": 1, "degraded": 0, "fail": 1},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "generate_release_risk_note.py",
            "--repo-root",
            str(tmp_path),
            "--failover-status-json",
            "docs/eval/failover_status.json",
            "--failover-fail-streak-threshold",
            "2",
        ],
    )
    assert grn.main() == 0
    payload = json.loads((docs_eval / "release_risk_note_auto.json").read_text(encoding="utf-8"))
    assert payload["gate_decision"] == "WARN"
    assert payload["violations"] == []
    assert payload["warnings"]
