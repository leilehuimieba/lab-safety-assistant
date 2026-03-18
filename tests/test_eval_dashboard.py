from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import generate_eval_dashboard as ged


def test_parse_dt_uses_fallback_run_id() -> None:
    dt = ged.parse_dt("", fallback_run_id="run_20260318_103000")
    assert dt.year == 2026
    assert dt.month == 3
    assert dt.day == 18
    assert dt.tzinfo is not None


def test_aggregate_weekly_groups_by_iso_week() -> None:
    records = [
        ged.RunRecord(
            source_type="smoke",
            run_id="run_20260317_090000",
            summary_path=Path("a.json"),
            generated_at=datetime(2026, 3, 17, 9, 0, tzinfo=timezone.utc),
            total_rows=10,
            metrics={
                "safety_refusal_rate": 0.9,
                "emergency_pass_rate": 0.8,
                "qa_pass_rate": 0.7,
                "coverage_rate": 1.0,
                "latency_p95_ms": 1500.0,
            },
            targets=ged.DEFAULT_TARGETS.copy(),
        ),
        ged.RunRecord(
            source_type="smoke",
            run_id="run_20260318_090000",
            summary_path=Path("b.json"),
            generated_at=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
            total_rows=20,
            metrics={
                "safety_refusal_rate": 1.0,
                "emergency_pass_rate": 0.9,
                "qa_pass_rate": 0.8,
                "coverage_rate": 1.0,
                "latency_p95_ms": 1200.0,
            },
            targets=ged.DEFAULT_TARGETS.copy(),
        ),
    ]
    weekly = ged.aggregate_weekly(records)
    assert len(weekly) == 1
    row = weekly[0]
    assert row["run_count"] == 2
    assert row["total_rows_avg"] == 15
    assert abs(float(row["qa_pass_rate"]) - 0.75) < 1e-6


def test_collect_records_reads_summary_json(tmp_path: Path) -> None:
    repo = tmp_path
    run_dir = repo / "artifacts" / "eval_smoke_demo" / "run_20260318_111111"
    run_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "generated_at": "2026-03-18T11:11:11+08:00",
        "total_rows": 50,
        "metrics": {
            "safety_refusal_rate": 0.98,
            "emergency_pass_rate": 0.91,
            "qa_pass_rate": 0.86,
            "coverage_rate": 0.95,
            "latency_p95_ms": 1800.0,
        },
        "targets": ged.DEFAULT_TARGETS,
    }
    (run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")

    records = ged.collect_records(
        repo_root=repo,
        patterns=["artifacts/eval_smoke*/run_*/summary.json"],
        source_type="smoke",
    )
    assert len(records) == 1
    assert records[0].run_id == "run_20260318_111111"
    assert records[0].total_rows == 50
    assert records[0].metrics["qa_pass_rate"] == 0.86

