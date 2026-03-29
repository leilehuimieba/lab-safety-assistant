from __future__ import annotations

import sync_release_fix_plan_issues as srf


def test_parse_owner_to_assignees() -> None:
    assignees = srf.parse_owner_to_assignees("@alice, bob;charlie invalid_name!")
    assert assignees == ["alice", "bob", "charlie"]


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
