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
        "--limit",
        type=int,
        default=0,
        help="Optional eval row limit (0 = full eval set).",
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
        "--output-dir",
        str(smoke_output),
    ]
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
    if args.update_dashboard:
        print("Dashboard refreshed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
