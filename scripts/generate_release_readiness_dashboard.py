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
        return "优先修复主链路可用性，检查 Dify 网关/模型路由和网络连通性。"
    if "route_timeout_rate" in lowered:
        return "先降并发并排查 SSE 超时链路，必要时启用备用通道并重跑 canary。"
    if "failover latest result" in lowered or "fail streak" in lowered:
        return "定位主模型不可用原因，恢复后连续两轮回归验证再解除阻断。"
    if "timeout ratio" in lowered:
        return "提高请求稳定性（超时阈值、重试策略、模型通道），避免连续超时触发回退。"
    if "override mode not allowed" in lowered:
        return "关闭临时豁免或切换到允许的发布 profile 后再执行发布。"
    if "stale" in lowered:
        return "重新执行一键回归链路，刷新 failover/status/risk_note 后重验。"
    if "latency_p95_ms" in lowered:
        return "优化提示词和检索链路，降低响应时延或调整限流策略。"
    return "按违规描述逐项修复后，重跑一键发布校验链路。"


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
        ]
    )
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text("\n".join(lines), encoding="utf-8")

    write_blocker_csv(blocker_csv, blocker_rows)
    write_blocker_md(blocker_md, blocker_rows)

    print(f"release readiness dashboard: {output_json}")
    print(f"release readiness markdown: {output_md}")
    print(f"release blocker csv: {blocker_csv}")
    print(f"release blocker md: {blocker_md}")

    if args.fail_on_block and overall_status == "BLOCK":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
