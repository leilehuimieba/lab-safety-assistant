#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


MODEL_OUTAGE_MARKERS = [
    "model_not_found",
    "invokeserverunavailableerror",
    "server unavailable error",
    "no available openai account supports the requested model",
    "http_503",
    "503",
]


def now_tag() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%d_%H%M%S")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run live eval with automatic model-level failover (primary -> fallback)."
    )
    parser.add_argument("--repo-root", default=".", help="Repository root.")
    parser.add_argument("--workflow-id", required=True, help="Target workflow id.")
    parser.add_argument("--primary-model", default="gpt-5.2-codex", help="Primary model name.")
    parser.add_argument("--fallback-model", default="MiniMax-M2.5", help="Fallback model name.")
    parser.add_argument("--temperature", type=float, default=0.2, help="LLM temperature for model patch.")

    parser.add_argument("--dify-base-url", default="", help="Dify base URL. If empty, use env DIFY_BASE_URL.")
    parser.add_argument("--dify-app-key", default="", help="Dify app key. If empty, use env DIFY_APP_API_KEY.")
    parser.add_argument(
        "--fallback-dify-base-url",
        default=os.environ.get("DIFY_FALLBACK_BASE_URL", ""),
        help="Fallback Dify base URL for timeout retry channel.",
    )
    parser.add_argument(
        "--fallback-dify-app-key",
        default=os.environ.get("DIFY_FALLBACK_APP_API_KEY", ""),
        help="Fallback Dify app key for timeout retry channel.",
    )
    parser.add_argument("--limit", type=int, default=20, help="Eval row limit.")
    parser.add_argument("--dify-timeout", type=float, default=60.0, help="Per-request timeout seconds.")
    parser.add_argument("--dify-response-mode", choices=["streaming", "blocking"], default="streaming")
    parser.add_argument("--eval-concurrency", type=int, default=1, help="Eval concurrency.")
    parser.add_argument("--retry-on-timeout", type=int, default=1, help="Retry count before channel fallback.")
    parser.add_argument("--preflight-timeout", type=float, default=8.0, help="Dify /parameters preflight timeout.")
    parser.add_argument(
        "--chat-preflight-timeout", type=float, default=20.0, help="Dify /chat-messages preflight timeout."
    )
    parser.add_argument("--worker-log-container", default="docker-worker-1", help="Worker container for diagnosis.")
    parser.add_argument(
        "--skip-health-check",
        action="store_true",
        help="Skip pre-run health check (Dify + embedding channel).",
    )
    parser.add_argument(
        "--health-check-script",
        default="scripts/check_live_eval_health.py",
        help="Health check script path (relative to repo root or absolute path).",
    )
    parser.add_argument(
        "--embedding-containers",
        nargs="+",
        default=["docker-api-1", "docker-worker-1", "docker-plugin_daemon-1"],
        help="Containers that must reach embedding endpoint during health check.",
    )
    parser.add_argument("--embedding-host", default="host.docker.internal", help="Embedding host alias.")
    parser.add_argument("--embedding-port", type=int, default=11434, help="Embedding endpoint port.")
    parser.add_argument("--embedding-timeout", type=float, default=3.0, help="Embedding curl timeout seconds.")
    parser.add_argument("--skip-preflight", action="store_true", help="Skip /parameters preflight.")
    parser.add_argument("--skip-chat-preflight", action="store_true", help="Skip /chat-messages preflight.")
    parser.add_argument("--allow-skip-live", action="store_true", help="Allow skip when Dify creds missing.")
    parser.add_argument("--update-dashboard", action="store_true", help="Refresh dashboard after each run.")
    parser.add_argument("--skip-risk-note", action="store_true", help="Skip release risk note generation.")
    parser.add_argument("--skip-failure-analysis", action="store_true", help="Skip failure cluster generation.")
    parser.add_argument(
        "--timeout-failover-threshold",
        type=float,
        default=1.0,
        help="Trigger failover when timeout fetch_error ratio reaches this threshold (0-1, default=1.0).",
    )
    parser.add_argument(
        "--restore-primary-after-run",
        action="store_true",
        help="Restore primary model when script exits (default keeps active model).",
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


def parse_live_run_dir(stdout_text: str) -> Path:
    prefix = "Live smoke run:"
    for line in stdout_text.splitlines():
        text = line.strip()
        if text.startswith(prefix):
            return Path(text.split(prefix, 1)[1].strip())
    raise RuntimeError("Cannot parse live smoke run dir from regression output.")


def has_model_outage_marker(text: str) -> bool:
    lowered = (text or "").lower()
    return any(marker in lowered for marker in MODEL_OUTAGE_MARKERS)


def collect_fetch_errors(smoke_run_dir: Path) -> list[str]:
    csv_path = smoke_run_dir / "detailed_results.csv"
    if not csv_path.exists():
        return []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    errors: list[str] = []
    for row in rows:
        error = (row.get("fetch_error") or "").strip()
        if error:
            errors.append(error)
    return errors


def timeout_error_ratio(fetch_errors: list[str]) -> float:
    if not fetch_errors:
        return 0.0
    timeout_count = 0
    for item in fetch_errors:
        lowered = (item or "").lower()
        if "timed out" in lowered or "timeout" in lowered:
            timeout_count += 1
    return timeout_count / len(fetch_errors)


def patch_workflow_model(repo_root: Path, workflow_id: str, model_name: str, temperature: float) -> None:
    cmd = [
        sys.executable,
        str(repo_root / "scripts" / "patch_workflow_model.py"),
        "--repo-root",
        str(repo_root),
        "--workflow-id",
        workflow_id,
        "--model-name",
        model_name,
        "--temperature",
        str(temperature),
    ]
    completed = run_cmd(cmd, cwd=repo_root)
    if completed.returncode != 0:
        raise RuntimeError(
            f"patch_workflow_model failed for {model_name}:\n{completed.stdout}\n{completed.stderr}"
        )


def run_regression(repo_root: Path, args: argparse.Namespace) -> subprocess.CompletedProcess[str]:
    dify_base_url = args.dify_base_url.strip() or os.environ.get("DIFY_BASE_URL", "").strip()
    dify_app_key = args.dify_app_key.strip() or os.environ.get("DIFY_APP_API_KEY", "").strip()
    cmd = [
        sys.executable,
        str(repo_root / "scripts" / "run_eval_regression_pipeline.py"),
        "--repo-root",
        str(repo_root),
        "--dify-base-url",
        dify_base_url,
        "--dify-app-key",
        dify_app_key,
        "--limit",
        str(max(0, args.limit)),
        "--dify-timeout",
        str(args.dify_timeout),
        "--dify-response-mode",
        args.dify_response_mode,
        "--eval-concurrency",
        str(max(1, args.eval_concurrency)),
        "--retry-on-timeout",
        str(max(0, args.retry_on_timeout)),
        "--preflight-timeout",
        str(max(1.0, args.preflight_timeout)),
        "--chat-preflight-timeout",
        str(max(1.0, args.chat_preflight_timeout)),
        "--worker-log-container",
        args.worker_log_container.strip(),
    ]
    if args.fallback_dify_base_url.strip():
        cmd.extend(["--fallback-dify-base-url", args.fallback_dify_base_url.strip()])
    if args.fallback_dify_app_key.strip():
        cmd.extend(["--fallback-dify-app-key", args.fallback_dify_app_key.strip()])
    if args.skip_preflight:
        cmd.append("--skip-preflight")
    if args.skip_chat_preflight:
        cmd.append("--skip-chat-preflight")
    if args.allow_skip_live:
        cmd.append("--allow-skip-live")
    if args.update_dashboard:
        cmd.append("--update-dashboard")
    if args.skip_risk_note:
        cmd.append("--skip-risk-note")
    if args.skip_failure_analysis:
        cmd.append("--skip-failure-analysis")
    return run_cmd(cmd, cwd=repo_root)


def run_health_check(repo_root: Path, args: argparse.Namespace) -> subprocess.CompletedProcess[str]:
    dify_base_url = args.dify_base_url.strip() or os.environ.get("DIFY_BASE_URL", "").strip()
    dify_app_key = args.dify_app_key.strip() or os.environ.get("DIFY_APP_API_KEY", "").strip()
    script_path = Path(args.health_check_script)
    if not script_path.is_absolute():
        script_path = (repo_root / script_path).resolve()
    cmd = [
        sys.executable,
        str(script_path),
        "--repo-root",
        str(repo_root),
        "--dify-base-url",
        dify_base_url,
        "--dify-app-key",
        dify_app_key,
        "--response-mode",
        args.dify_response_mode,
        "--preflight-timeout",
        str(max(1.0, args.preflight_timeout)),
        "--chat-preflight-timeout",
        str(max(1.0, args.chat_preflight_timeout)),
        "--worker-log-container",
        args.worker_log_container.strip(),
        "--embedding-host",
        args.embedding_host,
        "--embedding-port",
        str(int(args.embedding_port)),
        "--embedding-timeout",
        str(max(1.0, args.embedding_timeout)),
        "--embedding-containers",
        *[c for c in args.embedding_containers if c.strip()],
    ]
    return run_cmd(cmd, cwd=repo_root)


def write_report(report_path: Path, payload: dict) -> None:
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path = report_path.with_suffix(".md")
    runs = payload.get("runs", {}) or {}
    primary = runs.get("primary", {}) or {}
    fallback = runs.get("fallback", {}) or {}
    lines = [
        "# Model Failover Eval Report",
        "",
        f"- generated_at: `{payload.get('generated_at', '')}`",
        f"- workflow_id: `{payload.get('workflow_id', '')}`",
        f"- primary_model: `{payload.get('primary_model', '')}`",
        f"- fallback_model: `{payload.get('fallback_model', '')}`",
        f"- failover_triggered: `{payload.get('failover_triggered', False)}`",
        f"- failover_reason: `{payload.get('failover_reason', '')}`",
        "",
        "## Runs",
        "",
        f"- primary_exit_code: `{primary.get('exit_code', 'NA')}`",
        f"- primary_run_dir: `{primary.get('run_dir', '')}`",
        f"- fallback_exit_code: `{fallback.get('exit_code', 'NA')}`",
        f"- fallback_run_dir: `{fallback.get('run_dir', '')}`",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    out_dir = repo_root / "artifacts" / "model_failover_eval" / f"run_{now_tag()}"
    out_dir.mkdir(parents=True, exist_ok=True)

    dify_base_url = args.dify_base_url.strip() or os.environ.get("DIFY_BASE_URL", "").strip()
    dify_app_key = args.dify_app_key.strip() or os.environ.get("DIFY_APP_API_KEY", "").strip()
    if not dify_base_url or not dify_app_key:
        raise SystemExit("Missing DIFY_BASE_URL or DIFY_APP_API_KEY (or corresponding CLI args).")

    report: dict = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "workflow_id": args.workflow_id,
        "primary_model": args.primary_model,
        "fallback_model": args.fallback_model,
        "failover_triggered": False,
        "failover_reason": "",
        "active_model_final": args.primary_model,
        "runs": {},
    }

    try:
        if not args.skip_health_check:
            health_result = run_health_check(repo_root, args)
            report["health_check"] = {
                "exit_code": health_result.returncode,
                "stdout_tail": (health_result.stdout or "")[-3000:],
                "stderr_tail": (health_result.stderr or "")[-2000:],
            }
            if health_result.returncode != 0:
                raise RuntimeError(
                    "Health check failed before failover eval.\n"
                    f"{(health_result.stdout or '')[-2000:]}\n{(health_result.stderr or '')[-2000:]}"
                )

        patch_workflow_model(repo_root, args.workflow_id, args.primary_model, args.temperature)
        primary_run = run_regression(repo_root, args)
        primary_merged = (primary_run.stdout or "") + "\n" + (primary_run.stderr or "")

        primary_run_dir = ""
        primary_fetch_errors: list[str] = []
        if primary_run.returncode == 0:
            try:
                parsed_dir = parse_live_run_dir(primary_run.stdout or "")
                primary_run_dir = str(parsed_dir)
                primary_fetch_errors = collect_fetch_errors(parsed_dir)
            except Exception:
                primary_run_dir = ""

        primary_timeout_ratio = timeout_error_ratio(primary_fetch_errors)
        report["runs"]["primary"] = {
            "exit_code": primary_run.returncode,
            "run_dir": primary_run_dir,
            "fetch_error_count": len(primary_fetch_errors),
            "timeout_error_ratio": round(primary_timeout_ratio, 4),
            "fetch_errors": primary_fetch_errors[:30],
            "stdout_tail": (primary_run.stdout or "")[-6000:],
            "stderr_tail": (primary_run.stderr or "")[-4000:],
        }

        failover_reason = ""
        if primary_run.returncode != 0 and has_model_outage_marker(primary_merged):
            failover_reason = "primary pipeline failed and output matched model outage markers"
        elif any(has_model_outage_marker(item) for item in primary_fetch_errors):
            failover_reason = "primary run completed but fetch_error contained model outage markers"
        elif (
            len(primary_fetch_errors) > 0
            and max(0.0, min(1.0, float(args.timeout_failover_threshold))) <= primary_timeout_ratio
        ):
            failover_reason = (
                "primary run completed but timeout ratio reached threshold "
                f"({primary_timeout_ratio:.2f} >= {max(0.0, min(1.0, float(args.timeout_failover_threshold))):.2f})"
            )

        if failover_reason:
            report["failover_triggered"] = True
            report["failover_reason"] = failover_reason

            patch_workflow_model(repo_root, args.workflow_id, args.fallback_model, args.temperature)
            fallback_run = run_regression(repo_root, args)
            fallback_dir = ""
            fallback_fetch_errors: list[str] = []
            if fallback_run.returncode == 0:
                try:
                    parsed_dir = parse_live_run_dir(fallback_run.stdout or "")
                    fallback_dir = str(parsed_dir)
                    fallback_fetch_errors = collect_fetch_errors(parsed_dir)
                except Exception:
                    fallback_dir = ""

            report["runs"]["fallback"] = {
                "exit_code": fallback_run.returncode,
                "run_dir": fallback_dir,
                "fetch_error_count": len(fallback_fetch_errors),
                "timeout_error_ratio": round(timeout_error_ratio(fallback_fetch_errors), 4),
                "fetch_errors": fallback_fetch_errors[:30],
                "stdout_tail": (fallback_run.stdout or "")[-6000:],
                "stderr_tail": (fallback_run.stderr or "")[-4000:],
            }

            if fallback_run.returncode != 0:
                raise RuntimeError(
                    "Fallback model regression failed.\n"
                    f"{(fallback_run.stdout or '')[-2000:]}\n{(fallback_run.stderr or '')[-2000:]}"
                )
            report["active_model_final"] = args.fallback_model
        elif primary_run.returncode != 0:
            raise RuntimeError(
                "Primary model regression failed (no model-outage marker detected).\n"
                f"{(primary_run.stdout or '')[-2000:]}\n{(primary_run.stderr or '')[-2000:]}"
            )
    finally:
        if args.restore_primary_after_run:
            try:
                patch_workflow_model(repo_root, args.workflow_id, args.primary_model, args.temperature)
                report["active_model_final"] = args.primary_model
            except Exception as exc:  # pragma: no cover
                report["restore_error"] = str(exc)

        report_path = out_dir / "model_failover_report.json"
        write_report(report_path, report)
        print(f"Failover report: {report_path}")

    if report.get("failover_triggered"):
        print(
            "Model failover triggered. "
            f"reason={report.get('failover_reason')} final_model={report.get('active_model_final')}"
        )
    else:
        primary_meta = (report.get("runs", {}) or {}).get("primary", {}) or {}
        fetch_error_count = int(primary_meta.get("fetch_error_count", 0) or 0)
        if fetch_error_count > 0:
            print(
                "Primary run completed with fetch errors. "
                f"final_model={report.get('active_model_final')} fetch_error_count={fetch_error_count}"
            )
        else:
            print(f"Primary model healthy. final_model={report.get('active_model_final')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
