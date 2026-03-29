from __future__ import annotations

import sys
from pathlib import Path

import sync_release_fix_plan_issues as srf


def test_parse_owner_to_assignees() -> None:
    assignees = srf.parse_owner_to_assignees("@alice, bob;charlie invalid_name!")
    assert assignees == ["alice", "bob", "charlie"]


def test_parse_owner_field_collects_invalid_tokens() -> None:
    parsed = srf.parse_owner_field("@alice, bad!name ; @team-b")
    assert parsed.valid == ["alice", "team-b"]
    assert parsed.invalid == ["bad!name"]


def test_build_issue_title_truncates() -> None:
    title = srf.build_issue_title("REL-FIX-01", "x" * 200)
    assert title.startswith("[Release Fix] REL-FIX-01 ")
    assert len(title) < 120
    assert title.endswith("...")


def test_index_issues_by_task() -> None:
    issues = [
        {"number": 1, "body": "<!-- RELEASE_FIX_TASK:REL-FIX-01 -->\n...", "state": "open"},
        {"number": 2, "body": "no marker"},
    ]
    idx = srf.index_issues_by_task(issues)
    assert "REL-FIX-01" in idx
    assert idx["REL-FIX-01"]["number"] == 1


def test_is_assignee_error_detection() -> None:
    assert srf.is_assignee_error(RuntimeError("422 Validation Failed: assignees could not be resolved"))
    assert not srf.is_assignee_error(RuntimeError("500 internal error"))


def test_dry_run_does_not_modify_fix_plan_csv(tmp_path: Path, monkeypatch) -> None:
    csv_path = tmp_path / "release_fix_plan_auto.csv"
    csv_path.write_text(
        (
            "task_id,priority,status,owner,eta,profiles,blocking_reason,recommended_action,verification_step,"
            "issue_number,issue_url,last_synced_at\n"
            "REL-FIX-01,P0,todo,alice,2026-03-30,demo,demo gate fail,do something,recheck,,, \n"
        ),
        encoding="utf-8",
    )
    before = csv_path.read_text(encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "sync_release_fix_plan_issues.py",
            "--repo-root",
            str(tmp_path),
            "--fix-plan-csv",
            str(csv_path),
            "--report-json",
            str(tmp_path / "sync_report.json"),
            "--report-md",
            str(tmp_path / "sync_report.md"),
            "--repo-slug",
            "demo/demo",
            "--assign-from-owner",
            "--dry-run",
            "--quiet",
        ],
    )
    assert srf.main() == 0
    after = csv_path.read_text(encoding="utf-8")
    assert after == before
