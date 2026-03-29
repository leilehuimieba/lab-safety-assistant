from __future__ import annotations

import json
import sys
from pathlib import Path

import validate_release_policy_schema as vps


def _valid_policy() -> dict:
    return {
        "version": "v5",
        "profiles": {
            "demo": {
                "allowed_gate_decisions": ["PASS", "WARN", "WARN_ONLY"],
                "max_violation_count": 2,
                "max_warning_count": 6,
                "allowed_override_modes": ["warn_only"],
                "freshness": {"max_risk_note_age_hours": 72, "max_failover_status_age_hours": 72},
                "route": {"min_route_success_rate": 0.0, "max_route_timeout_rate": 1.0},
                "latency": {"max_latency_p95_ms": 120000},
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
                "freshness": {"max_risk_note_age_hours": 24, "max_failover_status_age_hours": 24},
                "route": {"min_route_success_rate": 0.8, "max_route_timeout_rate": 0.2},
                "latency": {"max_latency_p95_ms": 30000},
                "failover": {
                    "allowed_latest_results": ["pass", "degraded"],
                    "max_latest_timeout_error_ratio": 0.4,
                    "max_fail_window": 1,
                    "max_fail_streak": 1,
                },
            },
        },
    }


def test_validate_release_policy_schema_pass(tmp_path: Path, monkeypatch) -> None:
    docs_eval = tmp_path / "docs" / "eval"
    docs_eval.mkdir(parents=True, exist_ok=True)
    (docs_eval / "release_policy_v5.json").write_text(json.dumps(_valid_policy(), ensure_ascii=False), encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        ["validate_release_policy_schema.py", "--repo-root", str(tmp_path), "--quiet"],
    )
    assert vps.main() == 0


def test_validate_release_policy_schema_fail_missing_prod(tmp_path: Path, monkeypatch) -> None:
    docs_eval = tmp_path / "docs" / "eval"
    docs_eval.mkdir(parents=True, exist_ok=True)
    payload = _valid_policy()
    payload["profiles"].pop("prod", None)
    (docs_eval / "release_policy_v5.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        ["validate_release_policy_schema.py", "--repo-root", str(tmp_path), "--quiet"],
    )
    assert vps.main() == 1


def test_validate_release_policy_schema_fail_invalid_ratio(tmp_path: Path, monkeypatch) -> None:
    docs_eval = tmp_path / "docs" / "eval"
    docs_eval.mkdir(parents=True, exist_ok=True)
    payload = _valid_policy()
    payload["profiles"]["prod"]["failover"]["max_latest_timeout_error_ratio"] = 2.5
    (docs_eval / "release_policy_v5.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        ["validate_release_policy_schema.py", "--repo-root", str(tmp_path), "--quiet"],
    )
    assert vps.main() == 1

