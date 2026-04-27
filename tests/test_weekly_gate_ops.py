from __future__ import annotations

import json
import sys
from pathlib import Path

import generate_weekly_gate_ops as gwgo


def test_generate_weekly_gate_ops_from_local_json(tmp_path: Path, monkeypatch) -> None:
    issues = [
        {
            "number": 101,
            "title": "[Eval Gate] 2026-03-22 gate failed",
            "state": "closed",
            "created_at": "2026-03-22T01:00:00Z",
            "updated_at": "2026-03-22T06:00:00Z",
            "labels": [{"name": "eval-gate-alert"}],
        },
        {
            "number": 102,
            "title": "[Eval Gate] 2026-03-24 gate failed",
            "state": "open",
            "created_at": "2026-03-24T01:00:00Z",
            "updated_at": "2026-03-24T08:00:00Z",
            "labels": [{"name": "eval-gate-alert"}, {"name": "p1-gate"}, {"name": "sla-missing"}],
        },
        {
            "number": 301,
            "title": "[Release Fix] REL-FIX-01 demo blocked",
            "state": "open",
            "created_at": "2026-03-23T02:00:00Z",
            "updated_at": "2026-03-28T05:00:00Z",
            "labels": [{"name": "release-fix-task"}, {"name": "priority-p0"}],
        },
        {
            "number": 302,
            "title": "[Release Fix] REL-FIX-02 prod blocked",
            "state": "closed",
            "created_at": "2026-03-24T02:00:00Z",
            "updated_at": "2026-03-27T05:00:00Z",
            "closed_at": "2026-03-27T05:00:00Z",
            "labels": [{"name": "release-fix-task"}, {"name": "priority-p0"}],
        },
    ]
    issues_json = tmp_path / "issues.json"
    issues_json.write_text(json.dumps(issues, ensure_ascii=False), encoding="utf-8")

    repo_root = tmp_path
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "generate_weekly_gate_ops.py",
            "--repo-root",
            str(repo_root),
            "--issues-json",
            str(issues_json),
            "--today",
            "2026-03-28",
            "--days",
            "7",
        ],
    )
    assert gwgo.main() == 0

    output = repo_root / "docs" / "eval" / "weekly_gate_ops.md"
    text = output.read_text(encoding="utf-8")
    assert "PASS Days | 5" in text
    assert "FAIL Days | 2" in text
    assert "P1 Days | 1" in text
    assert "Open Alerts | 1" in text
    assert "Open P1 Alerts | 1" in text
    assert "Open SLA Missing | 1" in text
    assert "## Release Fix P0 Summary" in text
    assert "Created in Window | 2" in text
    assert "Closed in Window | 1" in text
    assert "Open Now | 1" in text
    assert "#301" in text


def test_generate_weekly_gate_ops_with_failover_snapshot(tmp_path: Path, monkeypatch) -> None:
    issues = [
        {
            "number": 201,
            "title": "[Eval Gate] 2026-03-27 gate failed",
            "state": "open",
            "created_at": "2026-03-27T01:00:00Z",
            "updated_at": "2026-03-27T05:00:00Z",
            "labels": [{"name": "eval-gate-alert"}],
        }
    ]
    issues_json = tmp_path / "issues.json"
    issues_json.write_text(json.dumps(issues, ensure_ascii=False), encoding="utf-8")

    failover_status = {
        "generated_at": "2026-03-29T00:00:00+00:00",
        "window_days": 7,
        "window_counts": {"pass": 1, "degraded": 2, "fail": 1, "failover_triggered": 2},
        "latest": {
            "result": "degraded",
            "generated_at": "2026-03-29T00:00:00+00:00",
            "active_model_final": "gpt-5.2-codex",
            "failover_reason": "timeout ratio reached threshold",
        },
    }
    failover_path = tmp_path / "docs" / "eval" / "failover_status.json"
    failover_path.parent.mkdir(parents=True, exist_ok=True)
    failover_path.write_text(json.dumps(failover_status, ensure_ascii=False), encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "generate_weekly_gate_ops.py",
            "--repo-root",
            str(tmp_path),
            "--issues-json",
            str(issues_json),
            "--today",
            "2026-03-29",
            "--days",
            "7",
            "--failover-status-json",
            str(failover_path),
        ],
    )
    assert gwgo.main() == 0
    output = tmp_path / "docs" / "eval" / "weekly_gate_ops.md"
    text = output.read_text(encoding="utf-8")
    assert "## Failover Snapshot" in text
    assert "Failover DEGRADED | 2" in text
    assert "Latest Failover Result: `degraded`" in text
