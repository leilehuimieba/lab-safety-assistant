#!/usr/bin/env python3
"""
Validate docs/ops/release_fix_plan_auto.csv.
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


REQUIRED_FIELDS = [
    "task_id",
    "priority",
    "status",
    "owner",
    "eta",
    "profiles",
    "blocking_reason",
    "recommended_action",
    "verification_step",
]

ALLOWED_PRIORITY = {"P0", "P1", "P2", "P3"}
ALLOWED_STATUS = {"todo", "in_progress", "blocked", "done", "wont_fix"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate release fix plan csv.")
    parser.add_argument("--repo-root", default=".", help="Repository root path.")
    parser.add_argument(
        "--fix-plan-csv",
        default="docs/ops/release_fix_plan_auto.csv",
        help="Fix plan csv path.",
    )
    parser.add_argument("--quiet", action="store_true", help="Print concise output.")
    return parser.parse_args()


def resolve_path(repo_root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (repo_root / path).resolve()


def valid_date(value: str) -> bool:
    return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", value.strip()))


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    csv_path = resolve_path(repo_root, args.fix_plan_csv)

    if not csv_path.exists():
        print(f"release_fix_plan failed: file missing: {csv_path}")
        return 1

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        rows = list(reader)

    errors: list[str] = []
    missing_fields = [field for field in REQUIRED_FIELDS if field not in headers]
    if missing_fields:
        errors.append(f"missing required headers: {missing_fields}")

    seen_task_ids: set[str] = set()
    for idx, row in enumerate(rows, start=2):
        task_id = str(row.get("task_id", "") or "").strip()
        priority = str(row.get("priority", "") or "").strip().upper()
        status = str(row.get("status", "") or "").strip().lower()
        owner = str(row.get("owner", "") or "").strip()
        eta = str(row.get("eta", "") or "").strip()
        reason = str(row.get("blocking_reason", "") or "").strip()
        action = str(row.get("recommended_action", "") or "").strip()
        verify = str(row.get("verification_step", "") or "").strip()

        if not task_id:
            errors.append(f"row {idx}: task_id is empty")
        elif task_id in seen_task_ids:
            errors.append(f"row {idx}: duplicate task_id: {task_id}")
        seen_task_ids.add(task_id)

        if priority not in ALLOWED_PRIORITY:
            errors.append(f"row {idx}: invalid priority: {priority}")

        if status not in ALLOWED_STATUS:
            errors.append(f"row {idx}: invalid status: {status}")

        if not reason:
            errors.append(f"row {idx}: blocking_reason is empty")
        if not action:
            errors.append(f"row {idx}: recommended_action is empty")
        if not verify:
            errors.append(f"row {idx}: verification_step is empty")

        if status in {"in_progress", "blocked"} and priority == "P0":
            if not owner:
                errors.append(f"row {idx}: P0 task requires owner when status is {status}")
            if not eta:
                errors.append(f"row {idx}: P0 task requires eta when status is {status}")
            elif not valid_date(eta):
                errors.append(f"row {idx}: invalid eta format (YYYY-MM-DD): {eta}")

    if errors:
        if not args.quiet:
            print("release_fix_plan validation failed:")
            for item in errors:
                print(f"- {item}")
        else:
            print(f"release_fix_plan validation failed: {len(errors)} issue(s)")
        return 1

    if not args.quiet:
        print("release_fix_plan validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
