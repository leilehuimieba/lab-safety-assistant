from __future__ import annotations

import csv
from unittest.mock import patch
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


def test_resolve_parameters_endpoint_variants() -> None:
    assert rep.resolve_parameters_endpoint("http://localhost") == "http://localhost/v1/parameters"
    assert rep.resolve_parameters_endpoint("http://localhost/v1") == "http://localhost/v1/parameters"


def test_resolve_chat_endpoint_variants() -> None:
    assert rep.resolve_chat_endpoint("http://localhost") == "http://localhost/v1/chat-messages"
    assert rep.resolve_chat_endpoint("http://localhost/v1") == "http://localhost/v1/chat-messages"


def test_preflight_dify_success_mocked() -> None:
    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self, n: int = -1) -> bytes:
            return b'{"ok":true}'

    with patch("run_eval_regression_pipeline.urllib.request.urlopen", return_value=_Resp()):
        ok, detail = rep.preflight_dify("http://localhost", "app-xxx", 2.0)
    assert ok is True
    assert "ok latency=" in detail


def test_preflight_dify_chat_timeout_hint() -> None:
    with patch(
        "run_eval_regression_pipeline.urllib.request.urlopen",
        side_effect=TimeoutError("timed out"),
    ):
        ok, detail = rep.preflight_dify_chat("http://localhost", "app-xxx", 2.0)
    assert ok is False
    assert "chat timeout" in detail


def test_parse_worker_log_hints_embedding_unreachable() -> None:
    log_text = (
        "InvokeServerUnavailableError ... host.docker.internal', port=11434 ... "
        "Request to Plugin Daemon Service failed-500"
    )
    hints = rep.parse_worker_log_hints(log_text)
    merged = " ".join(hints)
    assert "11434" in merged
    assert "Plugin Daemon 500" in merged
    assert "InvokeServerUnavailableError" in merged
