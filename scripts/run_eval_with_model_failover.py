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
    parser.add_argument(
        "--canary-limit",
        type=int,
        default=3,
        help="Quick canary row count before full run (0 to disable canary).",
    )
    parser.add_argument(
        "--canary-timeout",
        type=float,
        default=20.0,
        help="Per-request timeout for canary run.",
    )
    parser.add_argument(
        "--canary-timeout-failover-threshold",
        type=float,
        default=1.0,
        help="Trigger model failover when canary timeout ratio reaches this threshold (0-1).",
    )
    parser.add_argument(
        "--canary-retry-on-timeout",
        type=int,
        default=0,
        help="Retry count used in canary run before channel fallback (default 0 for faster fail-fast).",
    )
    parser.add_argument("--skip-canary", action="store_true", help="Skip canary run and go full directly.")
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
        "--health-allow-chat-timeout-pass",
        action="store_true",
        help="Allow health check pass when only chat preflight timed out; canary will verify real traffic.",
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


def clamp_ratio(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def should_trigger_timeout_failover(fetch_errors: list[str], threshold: float) -> bool:
    if not fetch_errors:
        return False
    return timeout_error_ratio(fetch_errors) >= clamp_ratio(threshold)


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


def run_regression(
    repo_root: Path,
    args: argparse.Namespace,
    *,
    limit_override: int | None = None,
    timeout_override: float | None = None,
    retry_on_timeout_override: int | None = None,
    update_dashboard_override: bool | None = None,
    skip_failure_analysis_override: bool | None = None,
) -> subprocess.CompletedProcess[str]:
    dify_base_url = args.dify_base_url.strip() or os.environ.get("DIFY_BASE_URL", "").strip()
    dify_app_key = args.dify_app_key.strip() or os.environ.get("DIFY_APP_API_KEY", "").strip()
    effective_limit = max(0, args.limit if limit_override is None else limit_override)
    effective_timeout = args.dify_timeout if timeout_override is None else timeout_override
    effective_retry = max(0, args.retry_on_timeout if retry_on_timeout_override is None else retry_on_timeout_override)
    effective_update_dashboard = args.update_dashboard if update_dashboard_override is None else update_dashboard_override
    effective_skip_failure = (
        args.skip_failure_analysis if skip_failure_analysis_override is None else skip_failure_analysis_override
    )
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
        str(effective_limit),
        "--dify-timeout",
        str(effective_timeout),
        "--dify-response-mode",
        args.dify_response_mode,
        "--eval-concurrency",
        str(max(1, args.eval_concurrency)),
        "--retry-on-timeout",
        str(effective_retry),
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
    # If health check already ran, skip duplicate preflight in inner regression calls.
    skip_inner_preflight = bool(args.skip_preflight or (not args.skip_health_check))
    skip_inner_chat_preflight = bool(args.skip_chat_preflight or (not args.skip_health_check))

    if skip_inner_preflight:
        cmd.append("--skip-preflight")
    if skip_inner_chat_preflight:
        cmd.append("--skip-chat-preflight")
    if args.allow_skip_live:
        cmd.append("--allow-skip-live")
    if effective_update_dashboard:
        cmd.append("--update-dashboard")
    if args.skip_risk_note:
        cmd.append("--skip-risk-note")
    if effective_skip_failure:
        cmd.append("--skip-failure-analysis")
    return run_cmd(cmd, cwd=repo_root)


def summarize_run(completed: subprocess.CompletedProcess[str]) -> dict:
    run_dir = ""
    fetch_errors: list[str] = []
    if completed.returncode == 0:
        try:
            parsed_dir = parse_live_run_dir(completed.stdout or "")
            run_dir = str(parsed_dir)
            fetch_errors = collect_fetch_errors(parsed_dir)
        except Exception:
            run_dir = ""
    return {
        "exit_code": completed.returncode,
        "run_dir": run_dir,
        "fetch_error_count": len(fetch_errors),
        "timeout_error_ratio": round(timeout_error_ratio(fetch_errors), 4),
        "fetch_errors": fetch_errors[:30],
        "stdout_tail": (completed.stdout or "")[-6000:],
        "stderr_tail": (completed.stderr or "")[-4000:],
    }


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
    if args.health_allow_chat_timeout_pass:
        cmd.append("--allow-chat-timeout-pass")
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
    run_failed = False
    current_model = args.primary_model

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

        canary_enabled = (not args.skip_canary) and int(args.canary_limit) > 0
        effective_canary_limit = max(1, int(args.canary_limit))
        failover_reason = ""

        patch_workflow_model(repo_root, args.workflow_id, args.primary_model, args.temperature)
        current_model = args.primary_model

        primary_canary_meta: dict | None = None
        if canary_enabled:
            primary_canary_run = run_regression(
                repo_root,
                args,
                limit_override=effective_canary_limit,
                timeout_override=max(1.0, float(args.canary_timeout)),
                retry_on_timeout_override=max(0, int(args.canary_retry_on_timeout)),
                update_dashboard_override=False,
                skip_failure_analysis_override=True,
            )
            primary_canary_meta = summarize_run(primary_canary_run)
            primary_canary_meta["phase"] = "canary"
            report["runs"]["primary_canary"] = primary_canary_meta

            primary_canary_merged = (primary_canary_run.stdout or "") + "\n" + (primary_canary_run.stderr or "")
            if primary_canary_run.returncode != 0 and has_model_outage_marker(primary_canary_merged):
                failover_reason = "primary canary failed and output matched model outage markers"
            elif should_trigger_timeout_failover(
                primary_canary_meta.get("fetch_errors", []) or [],
                float(args.canary_timeout_failover_threshold),
            ):
                failover_reason = (
                    "primary canary timeout ratio reached threshold "
                    f"({primary_canary_meta.get('timeout_error_ratio', 0.0):.2f} >= "
                    f"{clamp_ratio(float(args.canary_timeout_failover_threshold)):.2f})"
                )
            elif primary_canary_run.returncode != 0:
                raise RuntimeError(
                    "Primary model canary failed (non-model-outage).\n"
                    f"{(primary_canary_run.stdout or '')[-2000:]}\n{(primary_canary_run.stderr or '')[-2000:]}"
                )

        need_primary_full = (not failover_reason) and not (
            canary_enabled
            and primary_canary_meta is not None
            and int(args.limit) > 0
            and int(args.limit) <= effective_canary_limit
        )
        if not need_primary_full and primary_canary_meta is not None:
            primary_meta = dict(primary_canary_meta)
            primary_meta["phase"] = "full_from_canary"
            report["runs"]["primary"] = primary_meta
        else:
            primary_run = run_regression(repo_root, args)
            primary_meta = summarize_run(primary_run)
            primary_meta["phase"] = "full"
            report["runs"]["primary"] = primary_meta

            primary_merged = (primary_run.stdout or "") + "\n" + (primary_run.stderr or "")
            primary_fetch_errors = primary_meta.get("fetch_errors", []) or []
            if primary_run.returncode != 0 and has_model_outage_marker(primary_merged):
                failover_reason = "primary pipeline failed and output matched model outage markers"
            elif any(has_model_outage_marker(item) for item in primary_fetch_errors):
                failover_reason = "primary run completed but fetch_error contained model outage markers"
            elif should_trigger_timeout_failover(primary_fetch_errors, float(args.timeout_failover_threshold)):
                failover_reason = (
                    "primary run completed but timeout ratio reached threshold "
                    f"({primary_meta.get('timeout_error_ratio', 0.0):.2f} >= "
                    f"{clamp_ratio(float(args.timeout_failover_threshold)):.2f})"
                )
            elif primary_run.returncode != 0:
                raise RuntimeError(
                    "Primary model regression failed (no model-outage marker detected).\n"
                    f"{(primary_run.stdout or '')[-2000:]}\n{(primary_run.stderr or '')[-2000:]}"
                )

        if failover_reason:
            report["failover_triggered"] = True
            report["failover_reason"] = failover_reason

            patch_workflow_model(repo_root, args.workflow_id, args.fallback_model, args.temperature)
            current_model = args.fallback_model

            fallback_canary_meta: dict | None = None
            if canary_enabled:
                fallback_canary_run = run_regression(
                    repo_root,
                    args,
                    limit_override=effective_canary_limit,
                    timeout_override=max(1.0, float(args.canary_timeout)),
                    retry_on_timeout_override=max(0, int(args.canary_retry_on_timeout)),
                    update_dashboard_override=False,
                    skip_failure_analysis_override=True,
                )
                fallback_canary_meta = summarize_run(fallback_canary_run)
                fallback_canary_meta["phase"] = "canary"
                report["runs"]["fallback_canary"] = fallback_canary_meta

                fallback_canary_merged = (fallback_canary_run.stdout or "") + "\n" + (fallback_canary_run.stderr or "")
                if fallback_canary_run.returncode != 0 and has_model_outage_marker(fallback_canary_merged):
                    raise RuntimeError(
                        "Fallback model canary failed (model outage marker detected).\n"
                        f"{(fallback_canary_run.stdout or '')[-2000:]}\n{(fallback_canary_run.stderr or '')[-2000:]}"
                    )
                if should_trigger_timeout_failover(
                    fallback_canary_meta.get("fetch_errors", []) or [],
                    float(args.canary_timeout_failover_threshold),
                ):
                    raise RuntimeError(
                        "Fallback model canary timed out at threshold. "
                        "Stop full run to avoid long ineffective wait."
                    )
                if fallback_canary_run.returncode != 0:
                    raise RuntimeError(
                        "Fallback model canary failed.\n"
                        f"{(fallback_canary_run.stdout or '')[-2000:]}\n{(fallback_canary_run.stderr or '')[-2000:]}"
                    )

            need_fallback_full = not (
                canary_enabled
                and fallback_canary_meta is not None
                and int(args.limit) > 0
                and int(args.limit) <= effective_canary_limit
            )
            if not need_fallback_full and fallback_canary_meta is not None:
                fallback_meta = dict(fallback_canary_meta)
                fallback_meta["phase"] = "full_from_canary"
                report["runs"]["fallback"] = fallback_meta
            else:
                fallback_run = run_regression(repo_root, args)
                fallback_meta = summarize_run(fallback_run)
                fallback_meta["phase"] = "full"
                report["runs"]["fallback"] = fallback_meta
                if fallback_run.returncode != 0:
                    raise RuntimeError(
                        "Fallback model regression failed.\n"
                        f"{(fallback_run.stdout or '')[-2000:]}\n{(fallback_run.stderr or '')[-2000:]}"
                    )

            report["active_model_final"] = args.fallback_model
            current_model = args.fallback_model
        else:
            report["active_model_final"] = args.primary_model
            current_model = args.primary_model
    except Exception:
        run_failed = True
        raise
    finally:
        should_restore_primary = bool(args.restore_primary_after_run or run_failed)
        if should_restore_primary and current_model != args.primary_model:
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
