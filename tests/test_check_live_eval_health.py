from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import check_live_eval_health as clh


class _Proc:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_check_embedding_channel_success(monkeypatch, tmp_path: Path) -> None:
    def _fake_run_cmd(cmd: list[str], cwd: Path):
        return _Proc(returncode=0, stdout='{"models":[{"name":"bge-m3"}]}')

    monkeypatch.setattr(clh, "run_cmd", _fake_run_cmd)
    ok, detail = clh.check_embedding_channel(
        repo_root=tmp_path,
        container="docker-worker-1",
        host_alias="host.docker.internal",
        port=11434,
        timeout_sec=3.0,
    )
    assert ok is True
    assert "models" in detail.lower()


def test_check_embedding_channel_failure(monkeypatch, tmp_path: Path) -> None:
    def _fake_run_cmd(cmd: list[str], cwd: Path):
        return _Proc(returncode=7, stdout="", stderr="could not connect")

    monkeypatch.setattr(clh, "run_cmd", _fake_run_cmd)
    ok, detail = clh.check_embedding_channel(
        repo_root=tmp_path,
        container="docker-worker-1",
        host_alias="host.docker.internal",
        port=11434,
        timeout_sec=3.0,
    )
    assert ok is False
    assert "curl_exit_7" in detail


def test_main_allows_chat_timeout_when_flag_enabled(monkeypatch, tmp_path: Path) -> None:
    args = Namespace(
        repo_root=str(tmp_path),
        dify_base_url="http://localhost:8080",
        dify_app_key="app-xxx",
        response_mode="streaming",
        preflight_timeout=8.0,
        chat_preflight_timeout=20.0,
        worker_log_container="docker-worker-1",
        embedding_containers=["docker-api-1"],
        embedding_host="host.docker.internal",
        embedding_port=11434,
        embedding_timeout=3.0,
        skip_embedding_check=False,
        allow_chat_timeout_pass=True,
        output_dir="artifacts/live_health",
    )
    monkeypatch.setattr(clh, "parse_args", lambda: args)
    monkeypatch.setattr(clh.rep, "preflight_dify", lambda *_: (True, "ok"))
    monkeypatch.setattr(clh.rep, "preflight_dify_chat", lambda *_: (False, "request_error: timed out; chat timeout"))
    monkeypatch.setattr(clh.rep, "collect_worker_log_hints", lambda *_: [])
    monkeypatch.setattr(clh, "check_embedding_channel", lambda **_: (True, "ok"))
    rc = clh.main()
    assert rc == 0
