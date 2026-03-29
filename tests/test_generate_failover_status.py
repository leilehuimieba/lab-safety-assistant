from __future__ import annotations

import json
from types import SimpleNamespace
from pathlib import Path

import generate_failover_status as gfs


def test_generate_failover_status_outputs_latest(tmp_path: Path) -> None:
    reports_root = tmp_path / "artifacts" / "model_failover_eval"
    run1 = reports_root / "run_20260329_100000"
    run2 = reports_root / "run_20260329_110000"
    run1.mkdir(parents=True, exist_ok=True)
    run2.mkdir(parents=True, exist_ok=True)

    (run1 / "model_failover_report.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-03-29T10:00:00+00:00",
                "result": "pass",
                "failover_triggered": False,
                "active_model_final": "gpt-5.2-codex",
                "runs": {"primary": {"fetch_error_count": 0, "timeout_error_ratio": 0.0}},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (run2 / "model_failover_report.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-03-29T11:00:00+00:00",
                "result": "degraded",
                "failover_triggered": True,
                "failover_reason": "timeout ratio reached threshold",
                "active_model_final": "MiniMax-M2.5",
                "runs": {"fallback": {"fetch_error_count": 1, "timeout_error_ratio": 1.0}},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    output_json = tmp_path / "docs" / "eval" / "failover_status.json"
    output_md = tmp_path / "docs" / "eval" / "failover_status.md"
    args = gfs.parse_args
    try:
        gfs.parse_args = lambda: SimpleNamespace(
            repo_root=str(tmp_path),
            reports_root=str(reports_root),
            output_json=str(output_json),
            output_md=str(output_md),
            days=7,
        )
        assert gfs.main() == 0
    finally:
        gfs.parse_args = args

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    latest = payload.get("latest") or {}
    assert latest.get("result") == "degraded"
    assert latest.get("active_model_final") == "MiniMax-M2.5"
    md_text = output_md.read_text(encoding="utf-8")
    assert "Latest" in md_text
    assert "degraded" in md_text
