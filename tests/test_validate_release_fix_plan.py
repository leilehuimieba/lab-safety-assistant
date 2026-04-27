from __future__ import annotations

import csv
import sys
from pathlib import Path

import validate_release_fix_plan as vrf


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    headers = [
        "task_id",
        "priority",
        "status",
        "owner",
        "eta",
        "profiles",
        "blocking_reason",
        "recommended_action",
        "verification_step",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def test_validate_release_fix_plan_pass(tmp_path: Path, monkeypatch) -> None:
    docs_ops = tmp_path / "docs" / "ops"
    docs_ops.mkdir(parents=True, exist_ok=True)
    _write_csv(
        docs_ops / "release_fix_plan_auto.csv",
        [
            {
                "task_id": "REL-FIX-01",
                "priority": "P0",
                "status": "in_progress",
                "owner": "alice",
                "eta": "2026-04-03",
                "profiles": "prod",
                "blocking_reason": "route_timeout_rate too high",
                "recommended_action": "Tune timeout",
                "verification_step": "rerun",
            }
        ],
    )
    monkeypatch.setattr(sys, "argv", ["validate_release_fix_plan.py", "--repo-root", str(tmp_path), "--quiet"])
    assert vrf.main() == 0


def test_validate_release_fix_plan_fail_missing_owner_for_p0(tmp_path: Path, monkeypatch) -> None:
    docs_ops = tmp_path / "docs" / "ops"
    docs_ops.mkdir(parents=True, exist_ok=True)
    _write_csv(
        docs_ops / "release_fix_plan_auto.csv",
        [
            {
                "task_id": "REL-FIX-01",
                "priority": "P0",
                "status": "in_progress",
                "owner": "",
                "eta": "2026-04-03",
                "profiles": "prod",
                "blocking_reason": "route_timeout_rate too high",
                "recommended_action": "Tune timeout",
                "verification_step": "rerun",
            }
        ],
    )
    monkeypatch.setattr(sys, "argv", ["validate_release_fix_plan.py", "--repo-root", str(tmp_path), "--quiet"])
    assert vrf.main() == 1


def test_validate_release_fix_plan_fail_duplicate_task_id(tmp_path: Path, monkeypatch) -> None:
    docs_ops = tmp_path / "docs" / "ops"
    docs_ops.mkdir(parents=True, exist_ok=True)
    _write_csv(
        docs_ops / "release_fix_plan_auto.csv",
        [
            {
                "task_id": "REL-FIX-01",
                "priority": "P1",
                "status": "todo",
                "owner": "",
                "eta": "",
                "profiles": "prod",
                "blocking_reason": "a",
                "recommended_action": "x",
                "verification_step": "rerun",
            },
            {
                "task_id": "REL-FIX-01",
                "priority": "P2",
                "status": "todo",
                "owner": "",
                "eta": "",
                "profiles": "demo",
                "blocking_reason": "b",
                "recommended_action": "y",
                "verification_step": "rerun",
            },
        ],
    )
    monkeypatch.setattr(sys, "argv", ["validate_release_fix_plan.py", "--repo-root", str(tmp_path), "--quiet"])
    assert vrf.main() == 1
