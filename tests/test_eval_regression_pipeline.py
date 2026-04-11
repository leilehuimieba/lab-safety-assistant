from __future__ import annotations

import csv
from typing import Any
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


def test_preflight_dify_chat_sse_ok() -> None:
    class _Resp:
        headers = {"Content-Type": "text/event-stream"}

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def readline(self) -> bytes:
            if not hasattr(self, "_idx"):
                self._idx = 0
            lines = [
                b"event: ping\n",
                b"\n",
                b'data: {"event":"workflow_started"}\n',
                b'data: {"event":"workflow_finished","data":{"status":"succeeded","error":null}}\n',
            ]
            if self._idx >= len(lines):
                return b""
            line = lines[self._idx]
            self._idx += 1
            return line

    with patch("run_eval_regression_pipeline.urllib.request.urlopen", return_value=_Resp()):
        ok, detail = rep.preflight_dify_chat("http://localhost", "app-xxx", 2.0, "streaming")
    assert ok is True
    assert "mode=sse" in detail
    assert "status=succeeded" in detail


def test_preflight_dify_chat_sse_workflow_failed() -> None:
    class _Resp:
        headers = {"Content-Type": "text/event-stream"}

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def readline(self) -> bytes:
            if not hasattr(self, "_idx"):
                self._idx = 0
            lines = [
                b'data: {"event":"workflow_started"}\n',
                b'data: {"event":"workflow_finished","data":{"status":"failed","error":"upstream 500"}}\n',
            ]
            if self._idx >= len(lines):
                return b""
            line = lines[self._idx]
            self._idx += 1
            return line

    with patch("run_eval_regression_pipeline.urllib.request.urlopen", return_value=_Resp()):
        ok, detail = rep.preflight_dify_chat("http://localhost", "app-xxx", 2.0, "streaming")
    assert ok is False
    assert "workflow_failed" in detail


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


def test_classify_preflight_detail_variants() -> None:
    assert rep.classify_preflight_detail("") == "empty"
    assert rep.classify_preflight_detail("http_401: unauthorized") == "auth_error"
    assert rep.classify_preflight_detail("http_403: error code 1010") == "http_403_1010"
    assert rep.classify_preflight_detail("request_error: timed out") == "timeout"
    assert rep.classify_preflight_detail("http_502: bad gateway") == "http_error"
    assert rep.classify_preflight_detail("request_error: [Errno 111] connection refused") == "request_error"
    assert rep.classify_preflight_detail("workflow_failed latency=123ms") == "workflow_failed"


def test_route_label_masks_path_details() -> None:
    assert rep.route_label("https://example.com/v1") == "https://example.com/v1"
    assert rep.route_label("https://example.com/v1/chat-messages") == "https://example.com/*"
    assert rep.route_label("") == "(empty)"


def test_evaluate_fallback_attempt_reasons() -> None:
    ok, reason = rep.evaluate_fallback_attempt(
        primary_base_url="https://a/v1",
        primary_app_key="k1",
        fallback_base_url="https://b/v1",
        fallback_app_key="k2",
        primary_detail="request_error: timed out",
    )
    assert ok is True
    assert reason == "fallback_allowed"

    ok, reason = rep.evaluate_fallback_attempt(
        primary_base_url="https://a/v1",
        primary_app_key="k1",
        fallback_base_url="",
        fallback_app_key="",
        primary_detail="request_error: timed out",
    )
    assert ok is False
    assert reason == "fallback_missing_config"

    ok, reason = rep.evaluate_fallback_attempt(
        primary_base_url="https://a/v1",
        primary_app_key="k1",
        fallback_base_url="https://a/v1",
        fallback_app_key="k1",
        primary_detail="request_error: timed out",
    )
    assert ok is False
    assert reason == "fallback_same_as_primary"

    ok, reason = rep.evaluate_fallback_attempt(
        primary_base_url="https://a/v1",
        primary_app_key="k1",
        fallback_base_url="https://b/v1",
        fallback_app_key="k2",
        primary_detail="http_401: authentication failed",
    )
    assert ok is False
    assert reason == "fallback_blocked_auth_error"

    ok, reason = rep.evaluate_fallback_attempt(
        primary_base_url="https://a/v1",
        primary_app_key="k1",
        fallback_base_url="https://b/v1",
        fallback_app_key="k2",
        primary_detail="request_error: timed out",
        active_route="fallback",
    )
    assert ok is False
    assert reason == "active_route_not_primary"


def test_run_preflight_with_retries_emits_diagnostics(capsys: Any) -> None:
    state = {"n": 0}

    def _check(_: str, __: str, ___: float) -> tuple[bool, str]:
        state["n"] += 1
        if state["n"] == 1:
            return False, "request_error: timed out"
        return True, "ok latency=3ms"

    ok, detail = rep.run_preflight_with_retries(
        _check,
        base_url="https://example.com/v1",
        app_key="k",
        timeout_sec=1.0,
        retries=2,
        stage="unit_preflight",
        route="primary",
    )
    out = capsys.readouterr().out
    assert ok is True
    assert "after_retry=1" in detail
    assert "unit_preflight attempt failed" in out
    assert "detail_category=timeout" in out
    assert "unit_preflight succeeded after retries" in out
