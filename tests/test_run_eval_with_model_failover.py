from __future__ import annotations

import csv
from argparse import Namespace
from pathlib import Path

import run_eval_with_model_failover as remf


def test_has_model_outage_marker_detects_known_patterns() -> None:
    assert remf.has_model_outage_marker("HTTP 503 model_not_found")
    assert remf.has_model_outage_marker("InvokeServerUnavailableError: Server Unavailable Error")
    assert remf.has_model_outage_marker("No available OpenAI account supports the requested model")
    assert remf.has_model_outage_marker("timeout only") is False


def test_parse_live_run_dir() -> None:
    stdout = "...\nLive smoke run: D:/repo/artifacts/eval_smoke_auto/run_20260329_130000\n..."
    run_dir = remf.parse_live_run_dir(stdout)
    assert run_dir.as_posix().endswith("run_20260329_130000")


def test_collect_fetch_errors_reads_non_empty_only(tmp_path: Path) -> None:
    run_dir = tmp_path / "run_1"
    run_dir.mkdir(parents=True, exist_ok=True)
    csv_path = run_dir / "detailed_results.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "id",
                "fetch_error",
            ],
        )
        writer.writeheader()
        writer.writerow({"id": "E1", "fetch_error": ""})
        writer.writerow({"id": "E2", "fetch_error": "http_503: model_not_found"})
        writer.writerow({"id": "E3", "fetch_error": "request_error: timed out"})

    errors = remf.collect_fetch_errors(run_dir)
    assert errors == ["http_503: model_not_found", "request_error: timed out"]


def test_timeout_error_ratio() -> None:
    assert remf.timeout_error_ratio([]) == 0.0
    ratio = remf.timeout_error_ratio(
        ["request_error: timed out", "request_error: timeout", "http_503: model_not_found"]
    )
    assert abs(ratio - (2 / 3)) < 1e-8


def test_run_health_check_invokes_script(monkeypatch, tmp_path: Path) -> None:
    captured: dict = {}

    class _Proc:
        def __init__(self):
            self.returncode = 0
            self.stdout = "ok"
            self.stderr = ""

    def _fake_run_cmd(cmd: list[str], cwd: Path):
        captured["cmd"] = cmd
        captured["cwd"] = cwd
        return _Proc()

    monkeypatch.setattr(remf, "run_cmd", _fake_run_cmd)
    args = Namespace(
        dify_base_url="http://localhost:8080",
        dify_app_key="app-xxx",
        health_check_script="scripts/check_live_eval_health.py",
        dify_response_mode="streaming",
        preflight_timeout=8.0,
        chat_preflight_timeout=20.0,
        worker_log_container="docker-worker-1",
        embedding_host="host.docker.internal",
        embedding_port=11434,
        embedding_timeout=3.0,
        embedding_containers=["docker-api-1", "docker-worker-1"],
    )
    result = remf.run_health_check(tmp_path, args)
    assert result.returncode == 0
    joined = " ".join(captured["cmd"])
    assert "check_live_eval_health.py" in joined
    assert "--embedding-containers" in captured["cmd"]
