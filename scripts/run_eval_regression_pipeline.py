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
from pathlib import Path


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
        "--skip-preflight",
        action="store_true",
        help="Skip Dify /v1/parameters preflight check before smoke run.",
    )
    parser.add_argument(
        "--preflight-timeout",
        type=float,
        default=8.0,
        help="Timeout seconds for Dify preflight check.",
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

    if not args.skip_preflight:
        ok, detail = preflight_dify(dify_base_url, dify_app_key, args.preflight_timeout)
        if not ok:
            raise RuntimeError(
                "Dify preflight failed. "
                f"base_url={dify_base_url} detail={detail}. "
                "You can use --skip-preflight to bypass temporarily."
            )
        print(f"Dify preflight passed: {detail}")

    eval_set = resolve_path(repo_root, args.eval_set)
    smoke_output = resolve_path(repo_root, args.smoke_output_dir)
    review_output = resolve_path(repo_root, args.review_output_dir)

    smoke_cmd = [
        python,
        str(repo_root / "scripts" / "eval_smoke.py"),
        "--eval-set",
        str(eval_set),
        "--use-dify",
        "--dify-base-url",
        dify_base_url,
        "--dify-app-key",
        dify_app_key,
        "--dify-timeout",
        str(args.dify_timeout),
        "--concurrency",
        str(max(1, args.eval_concurrency)),
        "--retry-on-timeout",
        str(max(0, args.retry_on_timeout)),
        "--output-dir",
        str(smoke_output),
    ]
    if args.fallback_dify_base_url.strip():
        smoke_cmd.extend(["--fallback-dify-base-url", args.fallback_dify_base_url.strip()])
    if args.fallback_dify_app_key.strip():
        smoke_cmd.extend(["--fallback-dify-app-key", args.fallback_dify_app_key.strip()])
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

    print(f"Live smoke run: {smoke_run_dir}")
    print(f"Auto review run: {review_run_dir}")
    if not args.skip_failure_analysis:
        print(f"Failure clusters: {failure_cluster_csv}")
        print(f"Failure report: {failure_cluster_md}")
        print(f"Top10 fix list: {top10_fix_csv}")
    if args.update_dashboard:
        print("Dashboard refreshed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
