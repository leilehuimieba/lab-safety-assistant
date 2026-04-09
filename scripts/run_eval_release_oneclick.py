#!/usr/bin/env python3
"""
One-click eval release pipeline:
1) (Optional) run model failover live eval
2) generate failover status snapshot
3) generate release risk note
4) validate eval gate with failover enforcement
5) write one-click report
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def now_tag() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%d_%H%M%S")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one-click eval release chain.")
    parser.add_argument("--repo-root", default=".", help="Repository root path.")
    parser.add_argument(
        "--output-root",
        default="artifacts/eval_release_oneclick",
        help="Output root for one-click report artifacts.",
    )
    parser.add_argument(
        "--skip-failover-eval",
        action="store_true",
        help="Skip run_eval_with_model_failover.py and only run post steps.",
    )
    parser.add_argument(
        "--skip-gate",
        action="store_true",
        help="Skip validate_eval_dashboard_gate.py and only generate status/risk note.",
    )
    parser.add_argument(
        "--skip-release-policy-check",
        action="store_true",
        help="Skip validate_release_policy.py step.",
    )
    parser.add_argument(
        "--release-policy-profile",
        default="demo",
        help="Release policy profile name (for example: demo/prod).",
    )
    parser.add_argument(
        "--release-policy-run-secondary",
        action="store_true",
        help="Run secondary release policy check in addition to --release-policy-profile.",
    )
    parser.add_argument(
        "--release-policy-secondary-profile",
        default="prod",
        help="Secondary release policy profile name.",
    )
    parser.add_argument(
        "--release-policy-enforce-secondary",
        action="store_true",
        help="Block one-click result when secondary profile check fails.",
    )
    parser.add_argument(
        "--release-policy-strict",
        action="store_true",
        help="Pass --strict to validate_release_policy.py.",
    )

    parser.add_argument("--workflow-id", default="", help="Workflow id (required unless --skip-failover-eval).")
    parser.add_argument("--primary-model", default="gpt-5.2-codex", help="Primary model name.")
    parser.add_argument("--fallback-model", default="MiniMax-M2.5", help="Fallback model name.")
    parser.add_argument("--temperature", type=float, default=0.2, help="Model patch temperature.")

    parser.add_argument("--dify-base-url", default=os.environ.get("DIFY_BASE_URL", ""), help="Dify base URL.")
    parser.add_argument("--dify-app-key", default=os.environ.get("DIFY_APP_API_KEY", ""), help="Dify app key.")
    parser.add_argument(
        "--fallback-dify-base-url",
        default=os.environ.get("DIFY_FALLBACK_BASE_URL", ""),
        help="Fallback Dify base URL.",
    )
    parser.add_argument(
        "--fallback-dify-app-key",
        default=os.environ.get("DIFY_FALLBACK_APP_API_KEY", ""),
        help="Fallback Dify app key.",
    )
    parser.add_argument("--allow-skip-live", action="store_true", help="Allow skip live eval when creds missing.")

    parser.add_argument("--limit", type=int, default=20, help="Eval row limit.")
    parser.add_argument("--dify-timeout", type=float, default=60.0, help="Per-request timeout seconds.")
    parser.add_argument(
        "--dify-response-mode",
        choices=["streaming", "blocking"],
        default="streaming",
        help="Dify response mode.",
    )
    parser.add_argument("--eval-concurrency", type=int, default=1, help="Eval concurrency.")
    parser.add_argument("--retry-on-timeout", type=int, default=1, help="Retry count before channel fallback.")

    parser.add_argument("--skip-health-check", action="store_true", help="Skip pre-run health check.")
    parser.add_argument(
        "--health-allow-chat-timeout-pass",
        action="store_true",
        help="Allow health pass when only chat preflight timeout happens.",
    )

    parser.add_argument(
        "--canary-limit",
        type=int,
        default=3,
        help="Canary row count before full run (0 disables canary).",
    )
    parser.add_argument("--canary-timeout", type=float, default=20.0, help="Per-request timeout in canary.")
    parser.add_argument(
        "--canary-timeout-failover-threshold",
        type=float,
        default=1.0,
        help="Failover threshold by canary timeout ratio.",
    )
    parser.add_argument(
        "--canary-retry-on-timeout",
        type=int,
        default=1,
        help="Retry count in canary phase.",
    )
    parser.add_argument("--skip-canary", action="store_true", help="Skip canary and run full directly.")
    parser.add_argument(
        "--timeout-failover-threshold",
        type=float,
        default=1.0,
        help="Failover threshold by full-run timeout ratio.",
    )
    parser.add_argument(
        "--restore-primary-after-run",
        action="store_true",
        help="Restore primary model when one-click script exits.",
    )
    parser.add_argument(
        "--skip-update-dashboard",
        action="store_true",
        help="Do not pass --update-dashboard to failover eval runner.",
    )
    parser.add_argument(
        "--skip-failure-analysis",
        action="store_true",
        help="Skip failure cluster analysis during failover eval run.",
    )

    parser.add_argument("--failover-days", type=int, default=7, help="Window days for failover status snapshot.")
    parser.add_argument("--failover-max-age-hours", type=float, default=72.0, help="Max age for failover status.")
    parser.add_argument(
        "--failover-fail-streak-threshold",
        type=int,
        default=2,
        help="Gate blocks only when consecutive fail streak reaches threshold.",
    )
    parser.add_argument(
        "--failover-allow-degraded",
        action="store_true",
        help="Gate/risk note tolerate degraded as warning-free.",
    )
    return parser.parse_args()


def run_cmd(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def sanitize_command(cmd: list[str]) -> list[str]:
    secret_flags = {"--dify-app-key", "--fallback-dify-app-key"}
    sanitized: list[str] = []
    i = 0
    while i < len(cmd):
        token = cmd[i]
        sanitized.append(token)
        if token in secret_flags and i + 1 < len(cmd):
            sanitized.append("***REDACTED***")
            i += 2
            continue
        i += 1
    return sanitized


def summarize_step(completed: subprocess.CompletedProcess[str], cmd: list[str]) -> dict[str, Any]:
    return {
        "command": sanitize_command(cmd),
        "exit_code": int(completed.returncode),
        "stdout_tail": (completed.stdout or "")[-5000:],
        "stderr_tail": (completed.stderr or "")[-3000:],
    }


def parse_failover_report_path(stdout_text: str) -> str:
    prefix = "Failover report:"
    for line in (stdout_text or "").splitlines():
        text = line.strip()
        if text.startswith(prefix):
            return text.split(prefix, 1)[1].strip()
    return ""


def resolve_path(repo_root: Path, path_like: str) -> Path:
    path = Path(path_like)
    if path.is_absolute():
        return path
    return (repo_root / path).resolve()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return raw if isinstance(raw, dict) else {}


def write_report(run_dir: Path, payload: dict[str, Any]) -> tuple[Path, Path]:
    json_path = run_dir / "eval_release_oneclick_report.json"
    md_path = run_dir / "eval_release_oneclick_report.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    risk = payload.get("risk_note", {}) if isinstance(payload.get("risk_note"), dict) else {}
    gate = payload.get("gate", {}) if isinstance(payload.get("gate"), dict) else {}
    release_policy = payload.get("release_policy", {}) if isinstance(payload.get("release_policy"), dict) else {}
    release_policy_secondary = (
        payload.get("release_policy_secondary", {})
        if isinstance(payload.get("release_policy_secondary"), dict)
        else {}
    )
    lines = [
        "# Eval Release One-Click Report",
        "",
        f"- Generated: `{payload.get('generated_at', '')}`",
        f"- Status: `{payload.get('status', '')}`",
        f"- Repo: `{payload.get('repo_root', '')}`",
        f"- Run Dir: `{payload.get('run_dir', '')}`",
        "",
        "## Decision Snapshot",
        f"- Risk Decision: `{risk.get('gate_decision', '')}`",
        f"- Risk Violations: `{len(risk.get('violations', []) if isinstance(risk.get('violations'), list) else [])}`",
        f"- Risk Warnings: `{len(risk.get('warnings', []) if isinstance(risk.get('warnings'), list) else [])}`",
        f"- Gate Enforced: `{gate.get('enforced', False)}`",
        f"- Gate Exit Code: `{gate.get('exit_code', 'NA')}`",
        f"- Release Policy Profile: `{release_policy.get('profile', '')}`",
        f"- Release Policy Exit Code: `{release_policy.get('exit_code', 'NA')}`",
        f"- Secondary Policy Profile: `{release_policy_secondary.get('profile', '')}`",
        f"- Secondary Policy Exit Code: `{release_policy_secondary.get('exit_code', 'NA')}`",
        "",
        "## Artifacts",
        f"- Failover Status JSON: `{payload.get('failover_status_json', '')}`",
        f"- Risk Note JSON: `{payload.get('risk_note_json', '')}`",
        f"- Risk Note MD: `{payload.get('risk_note_md', '')}`",
        f"- Failover Eval Report: `{payload.get('failover_eval_report', '')}`",
        f"- Release Policy JSON: `{release_policy.get('output_json', '')}`",
        f"- Release Policy MD: `{release_policy.get('output_md', '')}`",
        f"- Secondary Policy JSON: `{release_policy_secondary.get('output_json', '')}`",
        f"- Secondary Policy MD: `{release_policy_secondary.get('output_md', '')}`",
        "",
        "## Steps",
    ]
    for name, step in (payload.get("steps", {}) or {}).items():
        if not isinstance(step, dict):
            continue
        lines.append(
            f"- `{name}`: exit_code={step.get('exit_code', 'NA')}, command=`{' '.join(step.get('command', []))}`"
        )
    lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


def build_failover_eval_cmd(args: argparse.Namespace, repo_root: Path) -> list[str]:
    effective_canary_timeout = max(1.0, float(args.canary_timeout))
    if args.dify_response_mode == "blocking":
        effective_canary_timeout = max(effective_canary_timeout, min(max(1.0, float(args.dify_timeout)), 60.0))

    cmd = [
        sys.executable,
        str(repo_root / "scripts" / "run_eval_with_model_failover.py"),
        "--repo-root",
        str(repo_root),
        "--workflow-id",
        args.workflow_id.strip(),
        "--primary-model",
        args.primary_model,
        "--fallback-model",
        args.fallback_model,
        "--temperature",
        str(args.temperature),
        "--limit",
        str(max(0, int(args.limit))),
        "--dify-timeout",
        str(max(1.0, float(args.dify_timeout))),
        "--dify-response-mode",
        args.dify_response_mode,
        "--eval-concurrency",
        str(max(1, int(args.eval_concurrency))),
        "--retry-on-timeout",
        str(max(0, int(args.retry_on_timeout))),
        "--canary-limit",
        str(max(0, int(args.canary_limit))),
        "--canary-timeout",
        str(effective_canary_timeout),
        "--canary-timeout-failover-threshold",
        str(float(args.canary_timeout_failover_threshold)),
        "--canary-retry-on-timeout",
        str(max(0, int(args.canary_retry_on_timeout))),
        "--timeout-failover-threshold",
        str(float(args.timeout_failover_threshold)),
        "--skip-risk-note",
    ]
    if args.dify_base_url.strip():
        cmd.extend(["--dify-base-url", args.dify_base_url.strip()])
    if args.dify_app_key.strip():
        cmd.extend(["--dify-app-key", args.dify_app_key.strip()])
    if args.fallback_dify_base_url.strip():
        cmd.extend(["--fallback-dify-base-url", args.fallback_dify_base_url.strip()])
    if args.fallback_dify_app_key.strip():
        cmd.extend(["--fallback-dify-app-key", args.fallback_dify_app_key.strip()])

    if args.allow_skip_live:
        cmd.append("--allow-skip-live")
    if args.skip_health_check:
        cmd.append("--skip-health-check")
    if args.health_allow_chat_timeout_pass:
        cmd.append("--health-allow-chat-timeout-pass")
    if args.skip_canary:
        cmd.append("--skip-canary")
    if args.restore_primary_after_run:
        cmd.append("--restore-primary-after-run")
    if not args.skip_update_dashboard:
        cmd.append("--update-dashboard")
    if args.skip_failure_analysis:
        cmd.append("--skip-failure-analysis")
    return cmd


def main() -> int:
    args = parse_args()
    repo_root = resolve_path(Path(args.repo_root).resolve(), ".")
    if (not args.skip_failover_eval) and (not args.workflow_id.strip()):
        raise SystemExit("--workflow-id is required unless --skip-failover-eval is set.")

    run_dir = resolve_path(repo_root, args.output_root) / f"run_{now_tag()}"
    run_dir.mkdir(parents=True, exist_ok=True)

    report: dict[str, Any] = {
        "generated_at": now_iso(),
        "status": "running",
        "repo_root": str(repo_root),
        "run_dir": str(run_dir),
        "steps": {},
        "failover_eval_report": "",
        "failover_status_json": str(repo_root / "docs" / "eval" / "failover_status.json"),
        "risk_note_json": str(repo_root / "docs" / "eval" / "release_risk_note_auto.json"),
        "risk_note_md": str(repo_root / "docs" / "eval" / "release_risk_note_auto.md"),
        "risk_note": {},
        "gate": {"enforced": not args.skip_gate, "exit_code": 0},
    }

    try:
        if not args.skip_failover_eval:
            failover_cmd = build_failover_eval_cmd(args, repo_root)
            failover_run = run_cmd(failover_cmd, cwd=repo_root)
            report["steps"]["failover_eval"] = summarize_step(failover_run, failover_cmd)
            report["failover_eval_report"] = parse_failover_report_path(failover_run.stdout or "")
            if failover_run.returncode != 0:
                report["status"] = "failed:failover_eval"
                write_report(run_dir, report)
                print(f"One-click failed at failover_eval. Report: {run_dir}")
                return 1

        failover_status_cmd = [
            sys.executable,
            str(repo_root / "scripts" / "generate_failover_status.py"),
            "--repo-root",
            str(repo_root),
            "--days",
            str(max(1, int(args.failover_days))),
        ]
        failover_status_run = run_cmd(failover_status_cmd, cwd=repo_root)
        report["steps"]["generate_failover_status"] = summarize_step(failover_status_run, failover_status_cmd)
        if failover_status_run.returncode != 0:
            report["status"] = "failed:generate_failover_status"
            write_report(run_dir, report)
            print(f"One-click failed at generate_failover_status. Report: {run_dir}")
            return 1

        risk_note_cmd = [
            sys.executable,
            str(repo_root / "scripts" / "generate_release_risk_note.py"),
            "--repo-root",
            str(repo_root),
            "--failover-max-age-hours",
            str(max(1.0, float(args.failover_max_age_hours))),
            "--failover-fail-streak-threshold",
            str(max(1, int(args.failover_fail_streak_threshold))),
        ]
        if args.failover_allow_degraded:
            risk_note_cmd.append("--failover-allow-degraded")
        risk_note_run = run_cmd(risk_note_cmd, cwd=repo_root)
        report["steps"]["generate_release_risk_note"] = summarize_step(risk_note_run, risk_note_cmd)
        if risk_note_run.returncode != 0:
            report["status"] = "failed:generate_release_risk_note"
            write_report(run_dir, report)
            print(f"One-click failed at generate_release_risk_note. Report: {run_dir}")
            return 1

        risk_json = resolve_path(repo_root, "docs/eval/release_risk_note_auto.json")
        report["risk_note"] = read_json(risk_json)

        if not args.skip_gate:
            gate_cmd = [
                sys.executable,
                str(repo_root / "scripts" / "validate_eval_dashboard_gate.py"),
                "--repo-root",
                str(repo_root),
                "--enforce-failover-status",
                "--failover-max-age-hours",
                str(max(1.0, float(args.failover_max_age_hours))),
                "--failover-fail-streak-threshold",
                str(max(1, int(args.failover_fail_streak_threshold))),
            ]
            if args.failover_allow_degraded:
                gate_cmd.append("--failover-allow-degraded")

            gate_run = run_cmd(gate_cmd, cwd=repo_root)
            report["steps"]["validate_gate"] = summarize_step(gate_run, gate_cmd)
            report["gate"] = {"enforced": True, "exit_code": int(gate_run.returncode)}
            if gate_run.returncode != 0:
                report["status"] = "blocked_by_gate"
                json_path, md_path = write_report(run_dir, report)
                print(f"One-click completed with gate block. Report: {json_path}")
                print(f"Markdown: {md_path}")
                return 2

        if not args.skip_release_policy_check:
            policy_cmd = [
                sys.executable,
                str(repo_root / "scripts" / "validate_release_policy.py"),
                "--repo-root",
                str(repo_root),
                "--profile",
                str(args.release_policy_profile).strip() or "demo",
            ]
            if args.release_policy_strict:
                policy_cmd.append("--strict")
            policy_run = run_cmd(policy_cmd, cwd=repo_root)
            report["steps"]["validate_release_policy"] = summarize_step(policy_run, policy_cmd)
            report["release_policy"] = {
                "profile": str(args.release_policy_profile).strip() or "demo",
                "strict": bool(args.release_policy_strict),
                "exit_code": int(policy_run.returncode),
                "output_json": str(repo_root / "docs" / "eval" / "release_policy_check.json"),
                "output_md": str(repo_root / "docs" / "eval" / "release_policy_check.md"),
            }
            if policy_run.returncode != 0:
                report["status"] = "blocked_by_release_policy"
                json_path, md_path = write_report(run_dir, report)
                print(f"One-click completed with release policy block. Report: {json_path}")
                print(f"Markdown: {md_path}")
                return 2

            if args.release_policy_run_secondary:
                secondary_profile = str(args.release_policy_secondary_profile).strip() or "prod"
                secondary_json = repo_root / "docs" / "eval" / f"release_policy_check_{secondary_profile}.json"
                secondary_md = repo_root / "docs" / "eval" / f"release_policy_check_{secondary_profile}.md"
                policy_secondary_cmd = [
                    sys.executable,
                    str(repo_root / "scripts" / "validate_release_policy.py"),
                    "--repo-root",
                    str(repo_root),
                    "--profile",
                    secondary_profile,
                    "--output-json",
                    str(secondary_json),
                    "--output-md",
                    str(secondary_md),
                ]
                if args.release_policy_strict:
                    policy_secondary_cmd.append("--strict")
                policy_secondary_run = run_cmd(policy_secondary_cmd, cwd=repo_root)
                report["steps"]["validate_release_policy_secondary"] = summarize_step(
                    policy_secondary_run, policy_secondary_cmd
                )
                report["release_policy_secondary"] = {
                    "profile": secondary_profile,
                    "strict": bool(args.release_policy_strict),
                    "exit_code": int(policy_secondary_run.returncode),
                    "output_json": str(secondary_json),
                    "output_md": str(secondary_md),
                    "enforced": bool(args.release_policy_enforce_secondary),
                }
                if policy_secondary_run.returncode != 0 and args.release_policy_enforce_secondary:
                    report["status"] = "blocked_by_release_policy_secondary"
                    json_path, md_path = write_report(run_dir, report)
                    print(f"One-click completed with secondary release policy block. Report: {json_path}")
                    print(f"Markdown: {md_path}")
                    return 2

        report["status"] = "success"
        json_path, md_path = write_report(run_dir, report)
        print(f"Eval release one-click success. Report: {json_path}")
        print(f"Markdown: {md_path}")
        return 0
    except Exception as exc:
        report["status"] = "failed:exception"
        report["exception"] = str(exc)
        json_path, md_path = write_report(run_dir, report)
        print(f"One-click crashed: {exc}")
        print(f"Report: {json_path}")
        print(f"Markdown: {md_path}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
