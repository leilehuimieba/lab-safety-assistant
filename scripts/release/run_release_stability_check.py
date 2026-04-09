#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class RoundResult:
    round_index: int
    command: list[str]
    exit_code: int
    status: str
    report_path: str
    demo_policy_exit: int | None
    prod_policy_exit: int | None
    emergency_pass_rate: float | None
    qa_pass_rate: float | None
    coverage_rate: float | None
    safety_refusal_rate: float | None
    failover_latest_result: str
    error: str = ""


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def now_tag() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%d_%H%M%S")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run multi-round release stability check.")
    parser.add_argument("--repo-root", default=".", help="Repository root path.")
    parser.add_argument("--rounds", type=int, default=3, help="Number of rounds.")
    parser.add_argument("--interval-sec", type=int, default=30, help="Sleep seconds between rounds.")
    parser.add_argument(
        "--output-root",
        default="artifacts/release_stability_check",
        help="Output root directory for round artifacts.",
    )
    parser.add_argument(
        "--output-json",
        default="docs/eval/release_stability_check.json",
        help="Summary JSON output path.",
    )
    parser.add_argument(
        "--output-md",
        default="docs/eval/release_stability_check.md",
        help="Summary Markdown output path.",
    )
    parser.add_argument(
        "--continue-on-fail",
        action="store_true",
        help="Continue remaining rounds even if one round fails.",
    )

    parser.add_argument("--workflow-id", default="", help="Workflow id (required unless --skip-failover-eval).")
    parser.add_argument("--primary-model", default="gpt-5.2-codex", help="Primary model.")
    parser.add_argument("--fallback-model", default="MiniMax-M2.5", help="Fallback model.")
    parser.add_argument("--dify-base-url", default="", help="Dify base URL.")
    parser.add_argument("--dify-app-key", default="", help="Dify app key.")
    parser.add_argument("--limit", type=int, default=20, help="Eval row limit.")
    parser.add_argument("--dify-timeout", type=float, default=180.0, help="Per request timeout seconds.")
    parser.add_argument(
        "--dify-response-mode",
        choices=["streaming", "blocking"],
        default="streaming",
        help="Dify response mode passed to one-click eval.",
    )
    parser.add_argument("--eval-concurrency", type=int, default=1, help="Eval concurrency.")
    parser.add_argument("--retry-on-timeout", type=int, default=1, help="Retry count.")
    parser.add_argument("--skip-health-check", action="store_true", help="Skip health check in one-click.")
    parser.add_argument(
        "--health-allow-chat-timeout-pass",
        action="store_true",
        help="Allow one-click health check to pass when chat preflight only times out.",
    )
    parser.add_argument("--skip-canary", action="store_true", help="Skip canary in one-click.")
    parser.add_argument("--skip-failover-eval", action="store_true", help="Skip failover eval stage.")
    parser.add_argument("--canary-timeout", type=float, default=20.0, help="Canary timeout passed to one-click.")

    parser.add_argument("--failover-days", type=int, default=1, help="Failover status window days.")
    parser.add_argument("--failover-fail-streak-threshold", type=int, default=2, help="Fail streak threshold.")

    parser.add_argument("--release-policy-profile", default="demo", help="Primary release policy profile.")
    parser.add_argument("--release-policy-run-secondary", action="store_true", help="Run secondary profile.")
    parser.add_argument("--release-policy-secondary-profile", default="prod", help="Secondary profile.")
    parser.add_argument("--release-policy-enforce-secondary", action="store_true", help="Enforce secondary block.")
    parser.add_argument("--release-policy-strict", action="store_true", help="Run release policy with strict mode.")
    return parser.parse_args()


def resolve(repo_root: Path, rel_or_abs: str) -> Path:
    p = Path(rel_or_abs)
    if p.is_absolute():
        return p
    return (repo_root / p).resolve()


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


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def find_latest_report(round_output_root: Path) -> Path | None:
    reports = sorted(round_output_root.glob("run_*/eval_release_oneclick_report.json"))
    if not reports:
        return None
    return reports[-1]


def build_oneclick_cmd(args: argparse.Namespace, repo_root: Path, round_output_root: Path) -> list[str]:
    cmd: list[str] = [
        sys.executable,
        str(repo_root / "scripts" / "run_eval_release_oneclick.py"),
        "--repo-root",
        str(repo_root),
        "--output-root",
        str(round_output_root),
        "--release-policy-profile",
        str(args.release_policy_profile).strip() or "demo",
    ]
    if args.release_policy_run_secondary:
        cmd.extend(
            [
                "--release-policy-run-secondary",
                "--release-policy-secondary-profile",
                str(args.release_policy_secondary_profile).strip() or "prod",
            ]
        )
    if args.release_policy_enforce_secondary:
        cmd.append("--release-policy-enforce-secondary")
    if args.release_policy_strict:
        cmd.append("--release-policy-strict")

    if args.skip_failover_eval:
        cmd.append("--skip-failover-eval")
    else:
        cmd.extend(
            [
                "--workflow-id",
                args.workflow_id.strip(),
                "--primary-model",
                args.primary_model.strip(),
                "--fallback-model",
                args.fallback_model.strip(),
                "--limit",
                str(max(0, int(args.limit))),
                "--dify-timeout",
                str(max(1.0, float(args.dify_timeout))),
                "--dify-response-mode",
                args.dify_response_mode.strip(),
                "--eval-concurrency",
                str(max(1, int(args.eval_concurrency))),
                "--retry-on-timeout",
                str(max(0, int(args.retry_on_timeout))),
                "--canary-timeout",
                str(max(1.0, float(args.canary_timeout))),
            ]
        )
        if args.dify_base_url.strip():
            cmd.extend(["--dify-base-url", args.dify_base_url.strip()])
        if args.dify_app_key.strip():
            cmd.extend(["--dify-app-key", args.dify_app_key.strip()])
        if args.skip_health_check:
            cmd.append("--skip-health-check")
        if args.health_allow_chat_timeout_pass or args.dify_response_mode.strip() == "blocking":
            cmd.append("--health-allow-chat-timeout-pass")
        if args.skip_canary:
            cmd.append("--skip-canary")

    cmd.extend(
        [
            "--failover-days",
            str(max(1, int(args.failover_days))),
            "--failover-fail-streak-threshold",
            str(max(1, int(args.failover_fail_streak_threshold))),
        ]
    )
    return cmd


def summarize_round(round_index: int, cmd: list[str], exit_code: int, report_path: Path | None) -> RoundResult:
    if report_path is None:
        return RoundResult(
            round_index=round_index,
            command=cmd,
            exit_code=exit_code,
            status="missing_report",
            report_path="",
            demo_policy_exit=None,
            prod_policy_exit=None,
            emergency_pass_rate=None,
            qa_pass_rate=None,
            coverage_rate=None,
            safety_refusal_rate=None,
            failover_latest_result="",
            error="eval_release_oneclick_report.json not found",
        )

    payload = load_json(report_path)
    risk = payload.get("risk_note", {}) if isinstance(payload.get("risk_note"), dict) else {}
    metrics = risk.get("latest_metrics", {}) if isinstance(risk.get("latest_metrics"), dict) else {}
    failover_latest = risk.get("failover_latest", {}) if isinstance(risk.get("failover_latest"), dict) else {}
    demo_policy = payload.get("release_policy", {}) if isinstance(payload.get("release_policy"), dict) else {}
    prod_policy = payload.get("release_policy_secondary", {}) if isinstance(payload.get("release_policy_secondary"), dict) else {}

    return RoundResult(
        round_index=round_index,
        command=cmd,
        exit_code=exit_code,
        status=str(payload.get("status", "")).strip() or "unknown",
        report_path=str(report_path),
        demo_policy_exit=int(demo_policy.get("exit_code")) if str(demo_policy.get("exit_code", "")).isdigit() else None,
        prod_policy_exit=int(prod_policy.get("exit_code")) if str(prod_policy.get("exit_code", "")).isdigit() else None,
        emergency_pass_rate=float(metrics.get("emergency_pass_rate", 0.0) or 0.0) if metrics else None,
        qa_pass_rate=float(metrics.get("qa_pass_rate", 0.0) or 0.0) if metrics else None,
        coverage_rate=float(metrics.get("coverage_rate", 0.0) or 0.0) if metrics else None,
        safety_refusal_rate=float(metrics.get("safety_refusal_rate", 0.0) or 0.0) if metrics else None,
        failover_latest_result=str(failover_latest.get("result", "") or ""),
    )


def to_markdown(
    *,
    generated_at: str,
    overall: str,
    rounds: int,
    passed_rounds: int,
    round_items: list[RoundResult],
) -> str:
    lines: list[str] = []
    lines.append("# Release Stability Check")
    lines.append("")
    lines.append(f"- Generated: `{generated_at}`")
    lines.append(f"- Overall: `{overall}`")
    lines.append(f"- Rounds: `{rounds}`")
    lines.append(f"- Passed Rounds: `{passed_rounds}`")
    lines.append("")
    lines.append("| Round | Exit | Status | DemoPolicy | ProdPolicy | Emergency | QA | Coverage | Refusal | FailoverLatest |")
    lines.append("|---|---:|---|---:|---:|---:|---:|---:|---:|---|")
    for item in round_items:
        lines.append(
            "| "
            f"{item.round_index} | {item.exit_code} | {item.status} | "
            f"{item.demo_policy_exit if item.demo_policy_exit is not None else '-'} | "
            f"{item.prod_policy_exit if item.prod_policy_exit is not None else '-'} | "
            f"{item.emergency_pass_rate:.4f}" if item.emergency_pass_rate is not None else "| "
            f"{item.round_index} | {item.exit_code} | {item.status} | "
            f"{item.demo_policy_exit if item.demo_policy_exit is not None else '-'} | "
            f"{item.prod_policy_exit if item.prod_policy_exit is not None else '-'} | - "
        )
        # Replace malformed previous append with full row construction for clarity.
        lines.pop()
        lines.append(
            "| "
            f"{item.round_index} | "
            f"{item.exit_code} | "
            f"{item.status} | "
            f"{item.demo_policy_exit if item.demo_policy_exit is not None else '-'} | "
            f"{item.prod_policy_exit if item.prod_policy_exit is not None else '-'} | "
            f"{(f'{item.emergency_pass_rate:.4f}' if item.emergency_pass_rate is not None else '-')} | "
            f"{(f'{item.qa_pass_rate:.4f}' if item.qa_pass_rate is not None else '-')} | "
            f"{(f'{item.coverage_rate:.4f}' if item.coverage_rate is not None else '-')} | "
            f"{(f'{item.safety_refusal_rate:.4f}' if item.safety_refusal_rate is not None else '-')} | "
            f"{(item.failover_latest_result or '-')} |"
        )
    lines.append("")
    lines.append("## Round Reports")
    for item in round_items:
        lines.append(f"- Round {item.round_index}: `{item.report_path or 'N/A'}`")
        if item.error:
            lines.append(f"  - error: {item.error}")
    lines.append("")
    lines.append("## Release Suggestion")
    if overall == "PASS":
        lines.append("1. Release stability passed in all rounds, ready for release window.")
    else:
        lines.append("1. Release stability check failed, fix issues and rerun before release.")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    if not args.skip_failover_eval and not args.workflow_id.strip():
        raise SystemExit("--workflow-id is required unless --skip-failover-eval is set.")

    rounds = max(1, int(args.rounds))
    interval = max(0, int(args.interval_sec))
    output_root = resolve(repo_root, args.output_root) / f"run_{now_tag()}"
    output_root.mkdir(parents=True, exist_ok=True)

    round_items: list[RoundResult] = []
    for idx in range(1, rounds + 1):
        round_dir = output_root / f"round_{idx:02d}"
        round_dir.mkdir(parents=True, exist_ok=True)
        cmd = build_oneclick_cmd(args, repo_root, round_dir)
        print(f"[stability] round {idx}/{rounds} start")
        completed = run_cmd(cmd, cwd=repo_root)
        report_path = find_latest_report(round_dir)
        summary = summarize_round(idx, cmd, int(completed.returncode), report_path)
        round_items.append(summary)
        print(
            f"[stability] round {idx} done: exit={summary.exit_code}, "
            f"status={summary.status}, report={summary.report_path or 'N/A'}"
        )
        failed = summary.exit_code != 0 or summary.status != "success"
        if failed and not args.continue_on_fail:
            print("[stability] stop early due to failure (use --continue-on-fail to keep running).")
            break
        if idx < rounds and interval > 0:
            time.sleep(interval)

    passed_rounds = sum(1 for item in round_items if item.exit_code == 0 and item.status == "success")
    overall = "PASS" if (len(round_items) == rounds and passed_rounds == rounds) else "BLOCK"

    payload = {
        "generated_at": now_iso(),
        "overall": overall,
        "rounds_requested": rounds,
        "rounds_completed": len(round_items),
        "passed_rounds": passed_rounds,
        "output_root": str(output_root),
        "rounds": [item.__dict__ for item in round_items],
    }

    output_json = resolve(repo_root, args.output_json)
    output_md = resolve(repo_root, args.output_md)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md.write_text(
        to_markdown(
            generated_at=payload["generated_at"],
            overall=overall,
            rounds=rounds,
            passed_rounds=passed_rounds,
            round_items=round_items,
        ),
        encoding="utf-8",
    )

    print(f"[stability] overall={overall}")
    print(f"- output json: {output_json}")
    print(f"- output md: {output_md}")

    return 0 if overall == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
