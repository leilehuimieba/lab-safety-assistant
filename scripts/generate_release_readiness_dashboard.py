#!/usr/bin/env python3
"""
Generate release readiness dashboard and blocker TopN from release policy checks.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ACTION_PLAN_FIELDNAMES = [
    "task_id",
    "priority",
    "status",
    "owner",
    "eta",
    "profiles",
    "blocking_reason",
    "recommended_action",
    "verification_step",
    "issue_number",
    "issue_url",
    "last_synced_at",
]

ALLOWED_ACTION_STATUS = {"todo", "in_progress", "blocked", "done", "wont_fix"}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate release readiness dashboard from policy checks.")
    parser.add_argument("--repo-root", default=".", help="Repository root path.")
    parser.add_argument(
        "--profiles",
        default="demo,prod",
        help="Comma-separated policy profiles to validate.",
    )
    parser.add_argument(
        "--strict-profiles",
        default="demo,prod",
        help="Comma-separated profiles executed with --strict.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=10,
        help="Top blocker reasons to output.",
    )
    parser.add_argument(
        "--output-json",
        default="docs/eval/release_readiness_dashboard.json",
        help="Readiness dashboard json output path.",
    )
    parser.add_argument(
        "--output-md",
        default="docs/eval/release_readiness_dashboard.md",
        help="Readiness dashboard markdown output path.",
    )
    parser.add_argument(
        "--blocker-csv",
        default="docs/eval/release_blocker_topn.csv",
        help="Blocker TopN csv output path.",
    )
    parser.add_argument(
        "--blocker-md",
        default="docs/eval/release_blocker_topn.md",
        help="Blocker TopN markdown output path.",
    )
    parser.add_argument(
        "--action-plan-csv",
        default="docs/ops/release_fix_plan_auto.csv",
        help="Auto-generated release fix plan csv path.",
    )
    parser.add_argument(
        "--action-plan-md",
        default="docs/ops/release_fix_plan_auto.md",
        help="Auto-generated release fix plan markdown path.",
    )
    parser.add_argument(
        "--fail-on-block",
        action="store_true",
        help="Return non-zero when any profile status is BLOCK.",
    )
    return parser.parse_args()


def resolve_path(repo_root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (repo_root / path).resolve()


def to_repo_rel(path: Path, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


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
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


def classify_priority(reason: str) -> str:
    lowered = reason.lower()
    if "route_success_rate" in lowered or "route_timeout_rate" in lowered:
        return "P0"
    if "failover" in lowered or "fail streak" in lowered or "timeout ratio" in lowered:
        return "P0"
    if "stale" in lowered or "generated_at" in lowered:
        return "P1"
    if "override" in lowered:
        return "P1"
    if "latency_p95_ms" in lowered:
        return "P1"
    return "P2"


def suggest_action(reason: str) -> str:
    lowered = reason.lower()
    if "route_success_rate" in lowered:
        return "Recover primary route availability first; check Dify gateway, model routing, and network path."
    if "route_timeout_rate" in lowered:
        return "Reduce concurrency and investigate SSE timeout path; enable fallback channel and rerun canary."
    if "failover latest result" in lowered or "fail streak" in lowered:
        return "Identify why primary model is unavailable; require two consecutive healthy regressions before release."
    if "timeout ratio" in lowered:
        return "Improve request stability (timeout budget, retry policy, model channel) to prevent repeated failover."
    if "override mode not allowed" in lowered:
        return "Disable temporary override or switch to an allowed release profile before release."
    if "stale" in lowered:
        return "Rerun one-click regression to refresh failover/status/risk_note artifacts and validate again."
    if "latency_p95_ms" in lowered:
        return "Optimize prompt and retrieval path, reduce latency, and tune rate limits."
    return "Fix listed blockers and rerun one-click release validation."


def build_blocker_rows(policy_results: list[dict[str, Any]], top_n: int) -> list[dict[str, str]]:
    reason_counter: Counter[str] = Counter()
    reason_profiles: defaultdict[str, set[str]] = defaultdict(set)

    for item in policy_results:
        profile = str(item.get("profile", "")).strip()
        violations = item.get("violations")
        if not isinstance(violations, list):
            continue
        for v in violations:
            reason = str(v or "").strip()
            if not reason:
                continue
            reason_counter[reason] += 1
            if profile:
                reason_profiles[reason].add(profile)

    rows: list[dict[str, str]] = []
    for idx, (reason, count) in enumerate(reason_counter.most_common(max(1, top_n)), start=1):
        rows.append(
            {
                "rank": str(idx),
                "reason": reason,
                "count": str(count),
                "profiles": ",".join(sorted(reason_profiles.get(reason, set()))),
                "priority": classify_priority(reason),
                "recommended_action": suggest_action(reason),
            }
        )
    return rows


def write_blocker_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["rank", "reason", "count", "profiles", "priority", "recommended_action"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_blocker_md(path: Path, rows: list[dict[str, str]]) -> None:
    lines = [
        "# Release Blocker TopN",
        "",
        f"- Generated: `{now_iso()}`",
        "",
        "| Rank | Priority | Count | Profiles | Reason | Recommended Action |",
        "|---:|---|---:|---|---|---|",
    ]
    if rows:
        for row in rows:
            lines.append(
                f"| {row['rank']} | {row['priority']} | {row['count']} | {row['profiles']} | "
                f"{row['reason']} | {row['recommended_action']} |"
            )
    else:
        lines.append("| - | - | 0 | - | none | none |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_existing_action_plan(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        records: dict[str, dict[str, str]] = {}
        for row in reader:
            reason = str(row.get("blocking_reason", "") or "").strip()
            if not reason:
                continue
            records[reason] = {k: str(v or "").strip() for k, v in row.items()}
        return records


def build_action_plan_rows(
    blocker_rows: list[dict[str, str]],
    existing_by_reason: dict[str, dict[str, str]],
) -> list[dict[str, str]]:
    def parse_task_num(task_id: str) -> int | None:
        text = str(task_id or "").strip().upper()
        if not text.startswith("REL-FIX-"):
            return None
        raw = text.replace("REL-FIX-", "", 1).strip()
        if not raw.isdigit():
            return None
        try:
            return int(raw)
        except ValueError:
            return None

    rows: list[dict[str, str]] = []
    used_task_ids: set[str] = set()
    next_task_num = 1

    for record in existing_by_reason.values():
        existing_task_id = str(record.get("task_id", "")).strip()
        if not existing_task_id:
            continue
        parsed = parse_task_num(existing_task_id)
        if parsed is not None:
            next_task_num = max(next_task_num, parsed + 1)

    def alloc_task_id(preferred: str) -> str:
        nonlocal next_task_num
        candidate = str(preferred or "").strip()
        if candidate and candidate not in used_task_ids:
            used_task_ids.add(candidate)
            parsed = parse_task_num(candidate)
            if parsed is not None:
                next_task_num = max(next_task_num, parsed + 1)
            return candidate
        while True:
            candidate = f"REL-FIX-{next_task_num:02d}"
            next_task_num += 1
            if candidate in used_task_ids:
                continue
            used_task_ids.add(candidate)
            return candidate

    for item in blocker_rows:
        rank = str(item.get("rank", "")).strip()
        reason = str(item.get("reason", "")).strip()
        profiles = str(item.get("profiles", "")).strip()
        priority = str(item.get("priority", "P2")).strip() or "P2"
        recommended_action = str(item.get("recommended_action", "")).strip()
        existing = existing_by_reason.get(reason, {})
        existing_status = str(existing.get("status", "todo")).strip().lower()
        status = existing_status if existing_status in ALLOWED_ACTION_STATUS else "todo"
        preferred_task_id = str(existing.get("task_id", "")).strip()
        if not preferred_task_id:
            preferred_task_id = f"REL-FIX-{rank.zfill(2)}" if rank.isdigit() else ""
        task_id = alloc_task_id(preferred_task_id)
        rows.append(
            {
                "task_id": task_id,
                "priority": priority,
                "status": status,
                "owner": str(existing.get("owner", "")).strip(),
                "eta": str(existing.get("eta", "")).strip(),
                "profiles": profiles,
                "blocking_reason": reason,
                "recommended_action": recommended_action,
                "verification_step": "Re-run one-click release check and verify profile status is PASS.",
                "issue_number": str(existing.get("issue_number", "")).strip(),
                "issue_url": str(existing.get("issue_url", "")).strip(),
                "last_synced_at": str(existing.get("last_synced_at", "")).strip(),
            }
        )
    return rows


def write_action_plan_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ACTION_PLAN_FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in ACTION_PLAN_FIELDNAMES})


def write_action_plan_md(path: Path, rows: list[dict[str, str]]) -> None:
    status_counter: Counter[str] = Counter(str(row.get("status", "todo")).strip().lower() for row in rows)
    lines = [
        "# Release Fix Plan (Auto)",
        "",
        f"- Generated: `{now_iso()}`",
        f"- Total Tasks: `{len(rows)}`",
        f"- todo: `{status_counter.get('todo', 0)}`",
        f"- in_progress: `{status_counter.get('in_progress', 0)}`",
        f"- blocked: `{status_counter.get('blocked', 0)}`",
        f"- done: `{status_counter.get('done', 0)}`",
        "",
        "| Task ID | Priority | Status | Owner | ETA | Profiles | Blocking Reason | Recommended Action | Verification Step |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    if rows:
        for row in rows:
            lines.append(
                f"| {row['task_id']} | {row['priority']} | {row['status']} | {row['owner']} | {row['eta']} | "
                f"{row['profiles']} | {row['blocking_reason']} | {row['recommended_action']} | {row['verification_step']} |"
            )
    else:
        lines.append("| - | - | done | - | - | - | none | none | none |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()

    profiles = [p.strip() for p in str(args.profiles or "").split(",") if p.strip()]
    strict_profiles = {p.strip() for p in str(args.strict_profiles or "").split(",") if p.strip()}
    if not profiles:
        raise SystemExit("No profiles configured.")

    policy_results: list[dict[str, Any]] = []
    step_logs: list[dict[str, Any]] = []
    for profile in profiles:
        output_json = resolve_path(repo_root, f"docs/eval/release_policy_check_{profile}.json")
        output_md = resolve_path(repo_root, f"docs/eval/release_policy_check_{profile}.md")
        cmd = [
            sys.executable,
            str(repo_root / "scripts" / "validate_release_policy.py"),
            "--repo-root",
            str(repo_root),
            "--profile",
            profile,
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
            "--quiet",
        ]
        if profile in strict_profiles:
            cmd.append("--strict")
        run = run_cmd(cmd, cwd=repo_root)
        payload = load_json(output_json)
        if not payload:
            payload = {
                "profile": profile,
                "status": "BLOCK",
                "violations": [f"policy output missing for profile: {profile}"],
                "warnings": [],
            }
        payload["profile"] = profile
        payload["exit_code"] = int(run.returncode)
        policy_results.append(payload)
        step_logs.append(
            {
                "profile": profile,
                "exit_code": int(run.returncode),
                "stdout_tail": (run.stdout or "")[-2000:],
                "stderr_tail": (run.stderr or "")[-1200:],
                "output_json": str(output_json),
                "output_md": str(output_md),
            }
        )

    blocker_rows = build_blocker_rows(policy_results, top_n=max(1, int(args.top_n)))

    overall_status = "PASS"
    if any(str(item.get("status", "")).upper() == "BLOCK" for item in policy_results):
        overall_status = "BLOCK"

    dashboard_payload = {
        "generated_at": now_iso(),
        "overall_status": overall_status,
        "profiles": policy_results,
        "blocker_topn": blocker_rows,
        "steps": step_logs,
    }

    output_json = resolve_path(repo_root, args.output_json)
    output_md = resolve_path(repo_root, args.output_md)
    blocker_csv = resolve_path(repo_root, args.blocker_csv)
    blocker_md = resolve_path(repo_root, args.blocker_md)
    action_plan_csv = resolve_path(repo_root, args.action_plan_csv)
    action_plan_md = resolve_path(repo_root, args.action_plan_md)
    existing_action_plan = load_existing_action_plan(action_plan_csv)
    action_plan_rows = build_action_plan_rows(blocker_rows, existing_action_plan)

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(dashboard_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Release Readiness Dashboard",
        "",
        f"- Generated: `{dashboard_payload['generated_at']}`",
        f"- Overall Status: `{overall_status}`",
        "",
        "## Profile Matrix",
        "",
        "| Profile | Status | Violations | Warnings | Override Active |",
        "|---|---|---:|---:|---|",
    ]
    for item in policy_results:
        violations = item.get("violations")
        warnings = item.get("warnings")
        lines.append(
            f"| {item.get('profile', '')} | {item.get('status', '')} | "
            f"{len(violations) if isinstance(violations, list) else 0} | "
            f"{len(warnings) if isinstance(warnings, list) else 0} | "
            f"{item.get('override_active', False)} |"
        )
    lines.extend(
        [
            "",
            "## Blocker TopN",
            "",
            f"- CSV: `{to_repo_rel(blocker_csv, repo_root)}`",
            f"- MD: `{to_repo_rel(blocker_md, repo_root)}`",
            "",
            "## Auto Fix Plan",
            "",
            f"- CSV: `{to_repo_rel(action_plan_csv, repo_root)}`",
            f"- MD: `{to_repo_rel(action_plan_md, repo_root)}`",
            "",
        ]
    )
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text("\n".join(lines), encoding="utf-8")

    write_blocker_csv(blocker_csv, blocker_rows)
    write_blocker_md(blocker_md, blocker_rows)
    write_action_plan_csv(action_plan_csv, action_plan_rows)
    write_action_plan_md(action_plan_md, action_plan_rows)

    dashboard_payload["action_plan"] = {
        "count": len(action_plan_rows),
        "csv": to_repo_rel(action_plan_csv, repo_root),
        "md": to_repo_rel(action_plan_md, repo_root),
    }
    output_json.write_text(json.dumps(dashboard_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"release readiness dashboard: {output_json}")
    print(f"release readiness markdown: {output_md}")
    print(f"release blocker csv: {blocker_csv}")
    print(f"release blocker md: {blocker_md}")
    print(f"release fix plan csv: {action_plan_csv}")
    print(f"release fix plan md: {action_plan_md}")

    if args.fail_on_block and overall_status == "BLOCK":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
