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
