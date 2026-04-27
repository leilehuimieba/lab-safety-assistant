from __future__ import annotations

from datetime import date

import escalate_release_fix_overdue as erfo


def test_collect_overdue_tasks_filters_priority_and_status() -> None:
    rows = [
        {
            "task_id": "REL-FIX-01",
            "priority": "P0",
            "status": "in_progress",
            "eta": "2026-03-20",
            "issue_number": "12",
            "issue_url": "https://x/12",
            "owner": "alice",
            "blocking_reason": "demo gate fail",
        },
        {
            "task_id": "REL-FIX-02",
            "priority": "P0",
            "status": "done",
            "eta": "2026-03-18",
            "issue_number": "13",
            "issue_url": "https://x/13",
            "owner": "bob",
            "blocking_reason": "done",
        },
        {
            "task_id": "REL-FIX-03",
            "priority": "P1",
            "status": "blocked",
            "eta": "2026-03-18",
            "issue_number": "14",
            "issue_url": "https://x/14",
            "owner": "carol",
            "blocking_reason": "prod warning",
        },
    ]
    overdue = erfo.collect_overdue_tasks(rows, today=date(2026, 3, 29), priority_filter="P0")
    assert len(overdue) == 1
    assert overdue[0].task_id == "REL-FIX-01"
    assert overdue[0].overdue_days == 9


def test_build_overdue_comment_contains_daily_marker() -> None:
    task = erfo.OverdueTask(
        task_id="REL-FIX-01",
        issue_number=42,
        issue_url="https://example.com/42",
        owner="alice",
        status="blocked",
        eta="2026-03-20",
        overdue_days=9,
        reason="gate blocked",
    )
    text = erfo.build_overdue_comment(task, today=date(2026, 3, 29))
    assert "<!-- RELEASE_FIX_OVERDUE:REL-FIX-01:2026-03-29 -->" in text
    assert "Overdue Days: `9`" in text

