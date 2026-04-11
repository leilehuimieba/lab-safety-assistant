#!/usr/bin/env python3
"""
Run eval smoke + auto review pipeline, then refresh dashboard.

Primary purpose:
- Trigger a real regression run (Dify App API)
- Feed fresh smoke/review results into eval dashboard automatically
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import json
from pathlib import Path
from urllib.parse import urlparse


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run eval regression pipeline.")
    parser.add_argument("--repo-root", default=".", help="Repository root path.")
    parser.add_argument("--eval-set", default="eval_set_v1.csv", help="Eval set CSV path.")
    parser.add_argument(
        "--smoke-output-dir",
        default="artifacts/eval_smoke_auto",
        help="Smoke output root dir.",
    )
    parser.add_argument(
        "--review-output-dir",
        default="artifacts/eval_review_auto",
        help="Review output root dir.",
    )
    parser.add_argument(
        "--dify-base-url",
        default="",
        help="Dify base URL. If empty, use env DIFY_BASE_URL.",
    )
    parser.add_argument(
        "--dify-app-key",
        default="",
        help="Dify app key. If empty, use env DIFY_APP_API_KEY.",
    )
    parser.add_argument(
        "--fallback-dify-base-url",
        default=os.environ.get("DIFY_FALLBACK_BASE_URL", ""),
        help="Fallback Dify base URL when primary requests time out.",
    )
    parser.add_argument(
        "--fallback-dify-app-key",
        default=os.environ.get("DIFY_FALLBACK_APP_API_KEY", ""),
        help="Fallback Dify app key when primary requests time out.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional eval row limit (0 = full eval set).",
    )
    parser.add_argument(
        "--dify-timeout",
        type=float,
        default=90.0,
        help="Per-request timeout seconds for eval_smoke Dify calls.",
    )
    parser.add_argument(
        "--dify-response-mode",
        choices=["streaming", "blocking"],
        default="streaming",
        help="Response mode used by eval_smoke when calling Dify chat-messages.",
    )
    parser.add_argument(
        "--eval-concurrency",
        type=int,
        default=4,
        help="Parallel workers for eval_smoke in Dify mode.",
    )
    parser.add_argument(
        "--retry-on-timeout",
        type=int,
        default=0,
        help="Retry count on primary channel before switching to fallback.",
    )
    parser.add_argument(
        "--preflight-retries",
        type=int,
        default=1,
        help="Retry count for /parameters preflight before fallback/error.",
    )
    parser.add_argument(
        "--chat-preflight-retries",
        type=int,
        default=1,
        help="Retry count for /chat-messages preflight before fallback/error.",
    )
    parser.add_argument(
        "--skip-preflight",
        action="store_true",
        help="Skip Dify /v1/parameters preflight check before smoke run.",
    )
    parser.add_argument(
        "--skip-chat-preflight",
        action="store_true",
        help="Skip Dify /v1/chat-messages quick preflight check before smoke run.",
    )
    parser.add_argument(
        "--preflight-timeout",
        type=float,
        default=8.0,
        help="Timeout seconds for Dify preflight check.",
    )
    parser.add_argument(
        "--chat-preflight-timeout",
        type=float,
        default=20.0,
        help="Timeout seconds for Dify chat preflight check.",
    )
    parser.add_argument(
        "--worker-log-container",
        default="docker-worker-1",
        help="Docker worker container name for auto diagnosis when chat preflight fails.",
    )
    parser.add_argument(
        "--allow-skip-live",
        action="store_true",
        help="Allow skip when Dify credentials are missing.",
    )
    parser.add_argument(
        "--update-dashboard",
        action="store_true",
        help="Refresh eval dashboard after regression run.",
    )
    parser.add_argument(
        "--skip-risk-note",
        action="store_true",
        help="Skip auto generation of release risk note when dashboard is refreshed.",
    )
    parser.add_argument(
        "--skip-failure-analysis",
        action="store_true",
        help="Skip eval failure clustering and Top10 fix list generation.",
    )
    return parser.parse_args()


def resolve_path(repo_root: Path, raw: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = repo_root / path
    return path.resolve()


def run_cmd(cmd: list[str], cwd: Path) -> str:
    completed = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stdout or "") + "\n" + (completed.stderr or "")
        raise RuntimeError(f"Command failed ({completed.returncode}): {' '.join(cmd)}\n{detail}")
    return completed.stdout


def parse_run_dir(stdout: str, prefix: str) -> Path:
    pattern = re.compile(rf"{re.escape(prefix)}\s*:\s*(.+)")
    for line in stdout.splitlines():
        match = pattern.search(line.strip())
        if match:
            return Path(match.group(1).strip())
    raise RuntimeError(f"Cannot parse run directory from output by prefix: {prefix}")


def resolve_parameters_endpoint(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/v1"):
        return f"{normalized}/parameters"
    return f"{normalized}/v1/parameters"


def resolve_chat_endpoint(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/v1"):
        return f"{normalized}/chat-messages"
    return f"{normalized}/v1/chat-messages"


def preflight_dify(base_url: str, app_key: str, timeout_sec: float) -> tuple[bool, str]:
    endpoint = resolve_parameters_endpoint(base_url)
    request = urllib.request.Request(
        endpoint,
        headers={"Authorization": f"Bearer {app_key}"},
        method="GET",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=max(timeout_sec, 1.0)) as response:
            _ = response.read(200)
        latency_ms = (time.perf_counter() - started) * 1000
        return True, f"ok latency={latency_ms:.0f}ms"
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8", errors="ignore")
        return False, f"http_{exc.code}: {payload[:200]}"
    except Exception as exc:  # pragma: no cover
        return False, f"request_error: {exc}"


def is_auth_related_preflight_error(detail: str) -> bool:
    lowered = (detail or "").strip().lower()
    if not lowered:
        return False
    auth_markers = (
        "http_401",
        "authentication failed",
        "invalid_request_error",
        "invalid api key",
        "unauthorized",
    )
    return any(marker in lowered for marker in auth_markers)


def should_try_fallback_preflight_detail(detail: str) -> bool:
    lowered = (detail or "").strip().lower()
    if not lowered:
        return True
    if is_auth_related_preflight_error(lowered):
        return False
    # For non-auth failures, fallback channel is usually worth trying.
    return True


def classify_preflight_detail(detail: str) -> str:
    lowered = (detail or "").strip().lower()
    if not lowered:
        return "empty"
    if is_auth_related_preflight_error(lowered):
        return "auth_error"
    if "1010" in lowered and "http_403" in lowered:
        return "http_403_1010"
    if "timed out" in lowered or "timeout" in lowered:
        return "timeout"
    if lowered.startswith("http_"):
        return "http_error"
    if "request_error" in lowered:
        return "request_error"
    if "workflow_failed" in lowered:
        return "workflow_failed"
    return "other"


def route_label(base_url: str) -> str:
    raw = (base_url or "").strip()
    if not raw:
        return "(empty)"
    parsed = urlparse(raw)
    if parsed.scheme and parsed.netloc:
        path = parsed.path or ""
        path_suffix = path if path in ("", "/v1") else "/*"
        return f"{parsed.scheme}://{parsed.netloc}{path_suffix}"
    return raw


def evaluate_fallback_attempt(
    *,
    primary_base_url: str,
    primary_app_key: str,
    fallback_base_url: str,
    fallback_app_key: str,
    primary_detail: str,
    active_route: str = "primary",
) -> tuple[bool, str]:
    if active_route != "primary":
        return False, "active_route_not_primary"
    if not fallback_base_url or not fallback_app_key:
        return False, "fallback_missing_config"
    if fallback_base_url == primary_base_url and fallback_app_key == primary_app_key:
        return False, "fallback_same_as_primary"
    if not should_try_fallback_preflight_detail(primary_detail):
        return False, "fallback_blocked_auth_error"
    return True, "fallback_allowed"


def run_preflight_with_retries(
    check_fn,
    *,
    base_url: str,
    app_key: str,
    timeout_sec: float,
    retries: int,
    response_mode: str = "",
    stage: str = "preflight",
    route: str = "primary",
) -> tuple[bool, str]:
    attempts = max(1, int(retries) + 1)
    last_detail = ""
    for idx in range(attempts):
        if response_mode:
            ok, detail = check_fn(base_url, app_key, timeout_sec, response_mode)
        else:
            ok, detail = check_fn(base_url, app_key, timeout_sec)
        if ok:
            if idx > 0:
                print(
                    f"{stage} succeeded after retries: route={route} endpoint={route_label(base_url)} "
                    f"attempt={idx + 1}/{attempts} detail={detail}"
                )
                return True, f"{detail} after_retry={idx}"
            return True, detail
        last_detail = detail
        print(
            f"{stage} attempt failed: route={route} endpoint={route_label(base_url)} "
            f"attempt={idx + 1}/{attempts} detail_category={classify_preflight_detail(detail)} detail={detail}"
        )
    return False, last_detail


def preflight_dify_chat(
    base_url: str,
    app_key: str,
    timeout_sec: float,
    response_mode: str = "blocking",
) -> tuple[bool, str]:
    endpoint = resolve_chat_endpoint(base_url)
    payload = {
        "inputs": {},
        "query": "你好，请只回复“ok”。",
        "response_mode": response_mode,
        "conversation_id": "",
        "user": "eval-preflight",
        "auto_generate_name": False,
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=body,
        headers={
            "Authorization": f"Bearer {app_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    started = time.perf_counter()
    hard_deadline = started + max(timeout_sec, 1.0)
    try:
        with urllib.request.urlopen(request, timeout=max(timeout_sec, 1.0)) as response:
            content_type = str(response.headers.get("Content-Type", "") or "").lower()
            if "text/event-stream" in content_type:
                saw_sse_event = False
                while True:
                    if time.perf_counter() >= hard_deadline:
                        latency_ms = (time.perf_counter() - started) * 1000
                        return False, f"sse_preflight_timeout latency={latency_ms:.0f}ms"
                    raw_line = response.readline()
                    if not raw_line:
                        break
                    line = raw_line.decode("utf-8", errors="ignore").strip()
                    if not line or not line.startswith("data:"):
                        continue
                    payload_str = line[5:].strip()
                    if not payload_str or payload_str == "[DONE]":
                        continue
                    try:
                        event_obj = json.loads(payload_str)
                    except Exception:
                        continue
                    saw_sse_event = True
                    event_name = str(event_obj.get("event", "") or "").strip().lower()
                    if event_name == "workflow_finished":
                        latency_ms = (time.perf_counter() - started) * 1000
                        workflow_data = event_obj.get("data") if isinstance(event_obj, dict) else {}
                        workflow_status = ""
                        workflow_error = ""
                        if isinstance(workflow_data, dict):
                            workflow_status = str(workflow_data.get("status", "") or "").strip().lower()
                            workflow_error = str(workflow_data.get("error", "") or "").strip()
                        if workflow_status == "failed":
                            detail = f"workflow_failed latency={latency_ms:.0f}ms"
                            if workflow_error:
                                detail += f" error={workflow_error[:160]}"
                            return False, detail
                        return True, f"ok latency={latency_ms:.0f}ms mode=sse status={workflow_status or 'unknown'}"
                latency_ms = (time.perf_counter() - started) * 1000
                if saw_sse_event:
                    return False, f"missing_workflow_finished latency={latency_ms:.0f}ms"
                return False, f"empty_sse_events latency={latency_ms:.0f}ms"

            raw = response.read().decode("utf-8", errors="ignore")
        latency_ms = (time.perf_counter() - started) * 1000
        answer = ""
        try:
            obj = json.loads(raw)
            answer = str(obj.get("answer", "") or "").strip()
        except Exception:  # pragma: no cover
            answer = ""
        if not answer:
            return False, f"empty_answer latency={latency_ms:.0f}ms"
        return True, f"ok latency={latency_ms:.0f}ms"
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8", errors="ignore")
        return False, f"http_{exc.code}: {payload[:200]}"
    except Exception as exc:  # pragma: no cover
        text = str(exc)
        if "timed out" in text.lower():
            hint = "chat timeout"
            return False, f"request_error: {text}; {hint}"
        return False, f"request_error: {text}"


def parse_worker_log_hints(log_text: str) -> list[str]:
    hints: list[str] = []
    lowered = (log_text or "").lower()
    if "host.docker.internal" in lowered and "11434" in lowered:
        hints.append(
            "发现 embedding 通道疑似不可达：host.docker.internal:11434。请检查 Ollama/embedding 服务网络映射。"
        )
    if "request to plugin daemon service failed-500" in lowered:
        hints.append("发现 Plugin Daemon 500 错误。请检查模型插件配置与上游连接。")
    if "invokeserverunavailableerror" in lowered:
        hints.append("发现模型服务不可用异常（InvokeServerUnavailableError）。")
    return hints

def collect_worker_log_hints(container_name: str) -> list[str]:
    if not container_name.strip():
        return []
    cmd = ["docker", "logs", "--tail", "220", container_name.strip()]
    completed = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
        check=False,
    )
    merged = (completed.stdout or "") + "\n" + (completed.stderr or "")
    return parse_worker_log_hints(merged)


def build_auto_manual_review(detailed_results_path: Path, manual_csv_path: Path) -> None:
    manual_csv_path.parent.mkdir(parents=True, exist_ok=True)
    with detailed_results_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    fieldnames = [
        "id",
        "manual_case_pass",
        "manual_refusal_correct",
        "manual_keypoint_score",
        "manual_issue_tags",
        "manual_notes",
    ]
    with manual_csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "id": (row.get("id") or "").strip(),
                    "manual_case_pass": "",
                    "manual_refusal_correct": "",
                    "manual_keypoint_score": "",
                    "manual_issue_tags": "",
                    "manual_notes": "auto-pipeline: keep auto score, pending human review",
                }
            )


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    python = sys.executable

    dify_base_url = args.dify_base_url.strip() or os.environ.get("DIFY_BASE_URL", "").strip()
    dify_app_key = args.dify_app_key.strip() or os.environ.get("DIFY_APP_API_KEY", "").strip()
    fallback_dify_base_url = args.fallback_dify_base_url.strip()
    fallback_dify_app_key = args.fallback_dify_app_key.strip()

    if not dify_base_url or not dify_app_key:
        if args.allow_skip_live:
            print("Live regression skipped: missing DIFY_BASE_URL or DIFY_APP_API_KEY.")
            if args.update_dashboard:
                dashboard_cmd = [
                    python,
                    str(repo_root / "scripts" / "generate_eval_dashboard.py"),
                    "--repo-root",
                    str(repo_root),
                ]
                run_cmd(dashboard_cmd, cwd=repo_root)
                print("Dashboard refreshed using existing eval artifacts.")
            return 0
        raise SystemExit("Missing DIFY_BASE_URL or DIFY_APP_API_KEY for live regression.")

    active_dify_base_url = dify_base_url
    active_dify_app_key = dify_app_key
    active_route = "primary"

    print(
        "Live regression preflight config: "
        f"primary={route_label(dify_base_url)} "
        f"fallback={route_label(fallback_dify_base_url)} "
        f"fallback_configured={bool(fallback_dify_base_url and fallback_dify_app_key)} "
        f"fallback_distinct={bool(fallback_dify_base_url and fallback_dify_app_key and (fallback_dify_base_url != dify_base_url or fallback_dify_app_key != dify_app_key))} "
        f"preflight_retries={max(0, args.preflight_retries)} "
        f"chat_preflight_retries={max(0, args.chat_preflight_retries)}"
    )

    if not args.skip_preflight:
        ok, detail = run_preflight_with_retries(
            preflight_dify,
            base_url=active_dify_base_url,
            app_key=active_dify_app_key,
            timeout_sec=args.preflight_timeout,
            retries=args.preflight_retries,
            stage="dify_parameters_preflight",
            route=active_route,
        )
        if not ok:
            primary_detail = detail
            can_try_fallback, fallback_reason = evaluate_fallback_attempt(
                primary_base_url=dify_base_url,
                primary_app_key=dify_app_key,
                fallback_base_url=fallback_dify_base_url,
                fallback_app_key=fallback_dify_app_key,
                primary_detail=primary_detail,
                active_route=active_route,
            )
            print(
                "Dify preflight fallback decision: "
                f"allowed={can_try_fallback} reason={fallback_reason} "
                f"primary_detail_category={classify_preflight_detail(primary_detail)}"
            )
            if can_try_fallback:
                ok_fb, detail_fb = run_preflight_with_retries(
                    preflight_dify,
                    base_url=fallback_dify_base_url,
                    app_key=fallback_dify_app_key,
                    timeout_sec=args.preflight_timeout,
                    retries=args.preflight_retries,
                    stage="dify_parameters_preflight",
                    route="fallback",
                )
                if ok_fb:
                    active_dify_base_url = fallback_dify_base_url
                    active_dify_app_key = fallback_dify_app_key
                    active_route = "fallback"
                    print(
                        "Dify preflight switched to fallback route: "
                        f"primary_detail={primary_detail} fallback_detail={detail_fb}"
                    )
                else:
                    raise RuntimeError(
                        "Dify preflight failed on primary and fallback channels. "
                        f"primary_base_url={dify_base_url} primary_detail={primary_detail}; "
                        f"fallback_base_url={fallback_dify_base_url} fallback_detail={detail_fb}. "
                        "You can use --skip-preflight to bypass temporarily."
                    )
            else:
                raise RuntimeError(
                    "Dify preflight failed. "
                    f"base_url={active_dify_base_url} detail={primary_detail}. "
                    f"fallback_reason={fallback_reason}. "
                    "You can use --skip-preflight to bypass temporarily."
                )
        else:
            print(f"Dify preflight passed: route={active_route} detail={detail}")

    if not args.skip_chat_preflight:
        ok, detail = run_preflight_with_retries(
            preflight_dify_chat,
            base_url=active_dify_base_url,
            app_key=active_dify_app_key,
            timeout_sec=args.chat_preflight_timeout,
            retries=args.chat_preflight_retries,
            response_mode=args.dify_response_mode,
            stage="dify_chat_preflight",
            route=active_route,
        )
        if not ok:
            primary_detail = detail
            can_try_fallback, fallback_reason = evaluate_fallback_attempt(
                primary_base_url=dify_base_url,
                primary_app_key=dify_app_key,
                fallback_base_url=fallback_dify_base_url,
                fallback_app_key=fallback_dify_app_key,
                primary_detail=primary_detail,
                active_route=active_route,
            )
            print(
                "Dify chat preflight fallback decision: "
                f"allowed={can_try_fallback} reason={fallback_reason} "
                f"primary_detail_category={classify_preflight_detail(primary_detail)}"
            )
            if can_try_fallback:
                ok_fb, detail_fb = run_preflight_with_retries(
                    preflight_dify_chat,
                    base_url=fallback_dify_base_url,
                    app_key=fallback_dify_app_key,
                    timeout_sec=args.chat_preflight_timeout,
                    retries=args.chat_preflight_retries,
                    response_mode=args.dify_response_mode,
                    stage="dify_chat_preflight",
                    route="fallback",
                )
                if ok_fb:
                    active_dify_base_url = fallback_dify_base_url
                    active_dify_app_key = fallback_dify_app_key
                    active_route = "fallback"
                    print(
                        "Dify chat preflight switched to fallback route: "
                        f"primary_detail={primary_detail} fallback_detail={detail_fb}"
                    )
                else:
                    auto_hints = collect_worker_log_hints(args.worker_log_container)
                    hint_block = ""
                    if auto_hints:
                        hint_block = " Auto diagnosis: " + " | ".join(auto_hints)
                    raise RuntimeError(
                        "Dify chat preflight failed on primary and fallback channels. "
                        f"primary_base_url={dify_base_url} primary_detail={primary_detail}; "
                        f"fallback_base_url={fallback_dify_base_url} fallback_detail={detail_fb}. "
                        "You can use --skip-chat-preflight temporarily, but live regression may time out."
                        f"{hint_block}"
                    )
            else:
                auto_hints = collect_worker_log_hints(args.worker_log_container)
                hint_block = ""
                if auto_hints:
                    hint_block = " Auto diagnosis: " + " | ".join(auto_hints)
                raise RuntimeError(
                    "Dify chat preflight failed. "
                    f"base_url={active_dify_base_url} detail={primary_detail}. "
                    f"fallback_reason={fallback_reason}. "
                    "You can use --skip-chat-preflight temporarily, but live regression may time out."
                    f"{hint_block}"
                )
        else:
            print(f"Dify chat preflight passed: route={active_route} detail={detail}")

    print(f"Live regression route selected: {active_route} ({active_dify_base_url})")

    eval_set = resolve_path(repo_root, args.eval_set)
    smoke_output = resolve_path(repo_root, args.smoke_output_dir)
    review_output = resolve_path(repo_root, args.review_output_dir)

    smoke_fallback_base_url = fallback_dify_base_url
    smoke_fallback_app_key = fallback_dify_app_key
    if (
        active_route == "fallback"
        and dify_base_url
        and dify_app_key
        and (dify_base_url != active_dify_base_url or dify_app_key != active_dify_app_key)
    ):
        smoke_fallback_base_url = dify_base_url
        smoke_fallback_app_key = dify_app_key

    smoke_cmd = [
        python,
        str(repo_root / "scripts" / "eval_smoke.py"),
        "--eval-set",
        str(eval_set),
        "--use-dify",
        "--dify-base-url",
        active_dify_base_url,
        "--dify-app-key",
        active_dify_app_key,
        "--dify-timeout",
        str(args.dify_timeout),
        "--dify-response-mode",
        args.dify_response_mode,
        "--concurrency",
        str(max(1, args.eval_concurrency)),
        "--retry-on-timeout",
        str(max(0, args.retry_on_timeout)),
        "--output-dir",
        str(smoke_output),
    ]
    if smoke_fallback_base_url and smoke_fallback_app_key:
        if smoke_fallback_base_url != active_dify_base_url or smoke_fallback_app_key != active_dify_app_key:
            smoke_cmd.extend(["--fallback-dify-base-url", smoke_fallback_base_url])
            smoke_cmd.extend(["--fallback-dify-app-key", smoke_fallback_app_key])
    if args.limit > 0:
        smoke_cmd.extend(["--limit", str(args.limit)])

    smoke_stdout = run_cmd(smoke_cmd, cwd=repo_root)
    smoke_run_dir = parse_run_dir(smoke_stdout, "Smoke eval done")
    detailed_results = smoke_run_dir / "detailed_results.csv"
    if not detailed_results.exists():
        raise RuntimeError(f"detailed_results.csv not found: {detailed_results}")

    review_run_dir = review_output / smoke_run_dir.name
    manual_csv = review_run_dir / "manual_review_auto.csv"
    build_auto_manual_review(detailed_results, manual_csv)

    review_cmd = [
        python,
        str(repo_root / "scripts" / "eval_review.py"),
        "--detailed-results",
        str(detailed_results),
        "--manual-review-csv",
        str(manual_csv),
        "--output-dir",
        str(review_run_dir),
    ]
    review_stdout = run_cmd(review_cmd, cwd=repo_root)
    parse_run_dir(review_stdout, "Manual review merge done")

    failure_cluster_csv = review_run_dir / "eval_failure_clusters.csv"
    failure_cluster_md = review_run_dir / "eval_failure_clusters.md"
    top10_fix_csv = review_run_dir / "eval_top10_fix_list.csv"
    if not args.skip_failure_analysis:
        analyze_cmd = [
            python,
            str(repo_root / "scripts" / "analyze_eval_failures.py"),
            "--detailed-results",
            str(detailed_results),
            "--output-csv",
            str(failure_cluster_csv),
            "--output-md",
            str(failure_cluster_md),
            "--top10-csv",
            str(top10_fix_csv),
        ]
        run_cmd(analyze_cmd, cwd=repo_root)

    if args.update_dashboard:
        dashboard_cmd = [
            python,
            str(repo_root / "scripts" / "generate_eval_dashboard.py"),
            "--repo-root",
            str(repo_root),
        ]
        run_cmd(dashboard_cmd, cwd=repo_root)
        if not args.skip_risk_note:
            risk_note_cmd = [
                python,
                str(repo_root / "scripts" / "generate_release_risk_note.py"),
                "--repo-root",
                str(repo_root),
            ]
            run_cmd(risk_note_cmd, cwd=repo_root)

    print(f"Live smoke run: {smoke_run_dir}")
    print(f"Auto review run: {review_run_dir}")
    if not args.skip_failure_analysis:
        print(f"Failure clusters: {failure_cluster_csv}")
        print(f"Failure report: {failure_cluster_md}")
        print(f"Top10 fix list: {top10_fix_csv}")
    if args.update_dashboard:
        print("Dashboard refreshed.")
        if not args.skip_risk_note:
            print("Release risk note refreshed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
