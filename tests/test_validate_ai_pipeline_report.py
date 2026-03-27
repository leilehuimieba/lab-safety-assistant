from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def run_validator(report_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        str(Path("scripts") / "validate_ai_pipeline_report.py"),
        "--report",
        str(report_path),
        *args,
    ]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def test_validate_ai_pipeline_report_pass(tmp_path: Path) -> None:
    report = {
        "status": "success",
        "counts": {
            "candidate_rows": 20,
            "audit_pass_rows": 10,
            "recheck_pass_rows": 6,
        },
        "ai": {
            "audit": {"parse_error_rate": 0.05},
        },
        "merge_stat": {"appended_rows": 3},
    }
    report_path = tmp_path / "ai_oneclick_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")

    completed = run_validator(report_path, "--require-merge-appended")
    assert completed.returncode == 0
    assert "passed" in completed.stdout.lower()


def test_validate_ai_pipeline_report_fail_on_low_rate(tmp_path: Path) -> None:
    report = {
        "status": "success",
        "counts": {
            "candidate_rows": 20,
            "audit_pass_rows": 2,
            "recheck_pass_rows": 1,
        },
        "ai": {
            "audit": {"parse_error_rate": 0.35},
        },
        "merge_stat": {"appended_rows": 0},
    }
    report_path = tmp_path / "ai_oneclick_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")

    completed = run_validator(
        report_path,
        "--min-audit-pass-rate",
        "0.3",
        "--min-recheck-pass-rate",
        "0.2",
        "--max-audit-parse-error-rate",
        "0.2",
        "--require-merge-appended",
    )
    assert completed.returncode == 1
    assert "failed" in completed.stdout.lower()

