from __future__ import annotations

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
