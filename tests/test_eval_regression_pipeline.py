from __future__ import annotations

import csv
from pathlib import Path

import run_eval_regression_pipeline as rep


def test_parse_run_dir_from_stdout() -> None:
    stdout = "...\nSmoke eval done: D:/tmp/eval/run_20260318_120000\n..."
    path = rep.parse_run_dir(stdout, "Smoke eval done")
    assert path.as_posix().endswith("run_20260318_120000")


def test_build_auto_manual_review(tmp_path: Path) -> None:
    detailed = tmp_path / "detailed_results.csv"
    with detailed.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "question", "response"])
        writer.writeheader()
        writer.writerow({"id": "EVAL-0001", "question": "Q1", "response": "A1"})
        writer.writerow({"id": "EVAL-0002", "question": "Q2", "response": "A2"})

    manual = tmp_path / "manual_review_auto.csv"
    rep.build_auto_manual_review(detailed, manual)

    with manual.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2
    assert rows[0]["id"] == "EVAL-0001"
    assert rows[0]["manual_case_pass"] == ""

