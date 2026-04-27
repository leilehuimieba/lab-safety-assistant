from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import run_eval_release_oneclick as rero


def _cp(cmd: list[str], returncode: int, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(cmd, returncode, stdout=stdout, stderr=stderr)


def test_sanitize_command_redacts_keys() -> None:
    cmd = [
        "python",
        "scripts/run_eval_release_oneclick.py",
        "--dify-app-key",
        "app-secret",
        "--fallback-dify-app-key",
        "fallback-secret",
    ]
    sanitized = rero.sanitize_command(cmd)
    joined = " ".join(sanitized)
    assert "app-secret" not in joined
    assert "fallback-secret" not in joined
    assert joined.count("***REDACTED***") == 2


def test_parse_failover_report_path() -> None:
    stdout = "foo\nFailover report: D:/repo/artifacts/model_failover_eval/run_1/model_failover_report.json\nbar"
    assert rero.parse_failover_report_path(stdout).endswith("model_failover_report.json")


def test_main_skip_failover_eval_success(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path
    docs_eval = repo_root / "docs" / "eval"
    docs_eval.mkdir(parents=True, exist_ok=True)
    (docs_eval / "release_risk_note_auto.json").write_text(
        json.dumps(
            {
                "gate_decision": "PASS",
                "violations": [],
                "warnings": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    def _fake_run_cmd(cmd: list[str], cwd: Path):
        cmd_text = " ".join(cmd)
        if "generate_failover_status.py" in cmd_text:
            return _cp(cmd, 0, stdout="ok")
        if "generate_release_risk_note.py" in cmd_text:
            return _cp(cmd, 0, stdout="ok")
        if "validate_eval_dashboard_gate.py" in cmd_text:
            return _cp(cmd, 0, stdout="passed")
        if "validate_release_policy.py" in cmd_text:
            return _cp(cmd, 0, stdout="policy passed")
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(rero, "run_cmd", _fake_run_cmd)
    monkeypatch.setattr(rero, "now_tag", lambda: "20260329_160000")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_eval_release_oneclick.py",
            "--repo-root",
            str(repo_root),
            "--output-root",
            "artifacts/eval_release_oneclick",
            "--skip-failover-eval",
        ],
    )
    assert rero.main() == 0
    report_path = repo_root / "artifacts" / "eval_release_oneclick" / "run_20260329_160000" / "eval_release_oneclick_report.json"
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["status"] == "success"
    assert payload["gate"]["exit_code"] == 0
    assert "generate_failover_status" in payload["steps"]
    assert "generate_release_risk_note" in payload["steps"]
    assert "validate_gate" in payload["steps"]
    assert "validate_release_policy" in payload["steps"]


def test_main_gate_block_returns_2(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path
    docs_eval = repo_root / "docs" / "eval"
    docs_eval.mkdir(parents=True, exist_ok=True)
    (docs_eval / "release_risk_note_auto.json").write_text(
        json.dumps(
            {
                "gate_decision": "BLOCK",
                "violations": ["x"],
                "warnings": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    def _fake_run_cmd(cmd: list[str], cwd: Path):
        cmd_text = " ".join(cmd)
        if "generate_failover_status.py" in cmd_text:
            return _cp(cmd, 0, stdout="ok")
        if "generate_release_risk_note.py" in cmd_text:
            return _cp(cmd, 0, stdout="ok")
        if "validate_eval_dashboard_gate.py" in cmd_text:
            return _cp(cmd, 1, stdout="failed")
        if "validate_release_policy.py" in cmd_text:
            return _cp(cmd, 0, stdout="policy passed")
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(rero, "run_cmd", _fake_run_cmd)
    monkeypatch.setattr(rero, "now_tag", lambda: "20260329_160001")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_eval_release_oneclick.py",
            "--repo-root",
            str(repo_root),
            "--output-root",
            "artifacts/eval_release_oneclick",
            "--skip-failover-eval",
        ],
    )
    assert rero.main() == 2
    report_path = repo_root / "artifacts" / "eval_release_oneclick" / "run_20260329_160001" / "eval_release_oneclick_report.json"
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["status"] == "blocked_by_gate"
    assert payload["gate"]["exit_code"] == 1


def test_main_release_policy_block_returns_2(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path
    docs_eval = repo_root / "docs" / "eval"
    docs_eval.mkdir(parents=True, exist_ok=True)
    (docs_eval / "release_risk_note_auto.json").write_text(
        json.dumps(
            {
                "gate_decision": "PASS",
                "violations": [],
                "warnings": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    def _fake_run_cmd(cmd: list[str], cwd: Path):
        cmd_text = " ".join(cmd)
        if "generate_failover_status.py" in cmd_text:
            return _cp(cmd, 0, stdout="ok")
        if "generate_release_risk_note.py" in cmd_text:
            return _cp(cmd, 0, stdout="ok")
        if "validate_eval_dashboard_gate.py" in cmd_text:
            return _cp(cmd, 0, stdout="passed")
        if "validate_release_policy.py" in cmd_text:
            return _cp(cmd, 1, stdout="policy blocked")
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(rero, "run_cmd", _fake_run_cmd)
    monkeypatch.setattr(rero, "now_tag", lambda: "20260329_160002")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_eval_release_oneclick.py",
            "--repo-root",
            str(repo_root),
            "--output-root",
            "artifacts/eval_release_oneclick",
            "--skip-failover-eval",
        ],
    )
    assert rero.main() == 2
    report_path = repo_root / "artifacts" / "eval_release_oneclick" / "run_20260329_160002" / "eval_release_oneclick_report.json"
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["status"] == "blocked_by_release_policy"
    assert payload["release_policy"]["exit_code"] == 1


def test_main_requires_workflow_id_without_skip_failover(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_eval_release_oneclick.py",
            "--repo-root",
            str(tmp_path),
        ],
    )
    try:
        rero.main()
    except SystemExit as exc:
        assert "--workflow-id is required" in str(exc)
    else:
        raise AssertionError("Expected SystemExit for missing workflow id")


def test_main_secondary_policy_block_when_enforced(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path
    docs_eval = repo_root / "docs" / "eval"
    docs_eval.mkdir(parents=True, exist_ok=True)
    (docs_eval / "release_risk_note_auto.json").write_text(
        json.dumps({"gate_decision": "PASS", "violations": [], "warnings": []}, ensure_ascii=False),
        encoding="utf-8",
    )

    def _fake_run_cmd(cmd: list[str], cwd: Path):
        cmd_text = " ".join(cmd)
        if "generate_failover_status.py" in cmd_text:
            return _cp(cmd, 0, stdout="ok")
        if "generate_release_risk_note.py" in cmd_text:
            return _cp(cmd, 0, stdout="ok")
        if "validate_eval_dashboard_gate.py" in cmd_text:
            return _cp(cmd, 0, stdout="passed")
        if "validate_release_policy.py" in cmd_text and "--profile demo" in cmd_text:
            return _cp(cmd, 0, stdout="demo pass")
        if "validate_release_policy.py" in cmd_text and "--profile prod" in cmd_text:
            return _cp(cmd, 1, stdout="prod block")
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(rero, "run_cmd", _fake_run_cmd)
    monkeypatch.setattr(rero, "now_tag", lambda: "20260329_160003")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_eval_release_oneclick.py",
            "--repo-root",
            str(repo_root),
            "--output-root",
            "artifacts/eval_release_oneclick",
            "--skip-failover-eval",
            "--release-policy-run-secondary",
            "--release-policy-secondary-profile",
            "prod",
            "--release-policy-enforce-secondary",
        ],
    )
    assert rero.main() == 2
    report_path = repo_root / "artifacts" / "eval_release_oneclick" / "run_20260329_160003" / "eval_release_oneclick_report.json"
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["status"] == "blocked_by_release_policy_secondary"


def test_build_failover_eval_cmd_passes_inner_preflight_flags() -> None:
    args = argparse.Namespace(
        workflow_id="wf-1",
        primary_model="m1",
        fallback_model="m1",
        temperature=0.2,
        limit=20,
        dify_timeout=180.0,
        dify_response_mode="streaming",
        eval_concurrency=1,
        retry_on_timeout=1,
        canary_limit=3,
        canary_timeout=20.0,
        canary_timeout_failover_threshold=1.0,
        canary_retry_on_timeout=1,
        timeout_failover_threshold=1.0,
        dify_base_url="http://127.0.0.1:8080",
        dify_app_key="app-xxx",
        fallback_dify_base_url="",
        fallback_dify_app_key="",
        allow_skip_live=False,
        skip_health_check=True,
        health_allow_chat_timeout_pass=True,
        skip_preflight=True,
        skip_chat_preflight=True,
        skip_canary=True,
        restore_primary_after_run=False,
        skip_update_dashboard=False,
        skip_failure_analysis=False,
    )
    cmd = rero.build_failover_eval_cmd(args, Path("/tmp/repo"))
    assert "--skip-health-check" in cmd
    assert "--health-allow-chat-timeout-pass" in cmd
    assert "--skip-preflight" in cmd
    assert "--skip-chat-preflight" in cmd
