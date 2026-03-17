from __future__ import annotations

from pathlib import Path

import secret_scan as ss


def test_should_skip_line_for_redacted_marker() -> None:
    assert ss.should_skip_line("API Key: <REDACTED_LLM_API_KEY>")


def test_scan_file_detects_app_key(tmp_path: Path) -> None:
    repo_root = tmp_path
    file_path = repo_root / "sample.md"
    key = "app-" + "ABCDEFGHIJKLMNOPQRSTUVWX"
    file_path.write_text(f"App API Key: {key}\n", encoding="utf-8")

    findings = ss.scan_file(file_path, repo_root)
    assert findings
    assert findings[0][2] == "dify_app_key"


def test_scan_file_ignores_redacted_line(tmp_path: Path) -> None:
    repo_root = tmp_path
    file_path = repo_root / "safe.md"
    file_path.write_text("App API Key: <REDACTED_APP_API_KEY>\n", encoding="utf-8")

    findings = ss.scan_file(file_path, repo_root)
    assert findings == []
