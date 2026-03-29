#!/usr/bin/env python3
"""
Validate release readiness against versioned policy profiles (demo/prod).
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate release policy (v5).")
    parser.add_argument("--repo-root", default=".", help="Repository root path.")
    parser.add_argument(
        "--policy-json",
        default="docs/eval/release_policy_v5.json",
        help="Policy file path.",
    )
    parser.add_argument(
        "--profile",
        default="demo",
        help="Policy profile name (for example: demo/prod).",
    )
    parser.add_argument(
        "--risk-note-json",
        default="docs/eval/release_risk_note_auto.json",
        help="Release risk note json path.",
    )
    parser.add_argument(
        "--failover-status-json",
        default="docs/eval/failover_status.json",
        help="Failover status json path.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail when input files are missing/unreadable.",
    )
    parser.add_argument(
        "--output-json",
        default="docs/eval/release_policy_check.json",
        help="Validation output json path.",
    )
    parser.add_argument(
        "--output-md",
        default="docs/eval/release_policy_check.md",
        help="Validation output markdown path.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Print concise output only.",
    )
    return parser.parse_args()


def resolve_path(repo_root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (repo_root / path).resolve()


def parse_iso_dt(raw: Any) -> datetime | None:
    value = str(raw or "").strip()
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value).astimezone(timezone.utc)
    except ValueError:
        return None


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return payload if isinstance(payload, dict) else None


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def count_latest_fail_streak(recent_runs: list[dict[str, Any]]) -> int:
    streak = 0
    for item in reversed(recent_runs):
        result = str(item.get("result", "") or "").strip().lower()
        if result == "fail":
            streak += 1
            continue
        break
    return streak


def check_freshness(
    *,
    generated_at: datetime | None,
    max_age_hours: float,
    label: str,
    violations: list[str],
    warnings: list[str],
    strict: bool,
) -> None:
    if generated_at is None:
        message = f"{label} missing/invalid generated_at"
        if strict:
            violations.append(message)
        else:
            warnings.append(message)
        return
    age_hours = (datetime.now(timezone.utc) - generated_at).total_seconds() / 3600.0
    if age_hours > max(1.0, float(max_age_hours)):
        violations.append(f"{label} stale: age={age_hours:.1f}h > max={max(1.0, float(max_age_hours)):.1f}h")


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()

    policy_path = resolve_path(repo_root, args.policy_json)
    risk_path = resolve_path(repo_root, args.risk_note_json)
    failover_path = resolve_path(repo_root, args.failover_status_json)
    output_json = resolve_path(repo_root, args.output_json)
    output_md = resolve_path(repo_root, args.output_md)

    violations: list[str] = []
    warnings: list[str] = []

    policy = load_json(policy_path)
    if policy is None:
        print(f"release policy check failed: policy file missing/unreadable: {policy_path}")
        return 1

    profiles = policy.get("profiles")
    if not isinstance(profiles, dict):
        print("release policy check failed: policy.profiles invalid")
        return 1

    profile = profiles.get(args.profile)
    if not isinstance(profile, dict):
        print(f"release policy check failed: profile not found: {args.profile}")
        return 1

    risk = load_json(risk_path)
    if risk is None:
        message = f"risk note missing/unreadable: {risk_path}"
        if args.strict:
            print(f"release policy check failed: {message}")
            return 1
        warnings.append(message)
        risk = {}

    failover = load_json(failover_path)
    if failover is None:
        message = f"failover status missing/unreadable: {failover_path}"
        if args.strict:
            print(f"release policy check failed: {message}")
            return 1
        warnings.append(message)
        failover = {}

    allowed_gate_decisions = {
        str(item).strip().upper()
        for item in (profile.get("allowed_gate_decisions") or [])
        if str(item).strip()
    }
    gate_decision = str(risk.get("gate_decision", "") or "").strip().upper()
    if gate_decision and allowed_gate_decisions and gate_decision not in allowed_gate_decisions:
        violations.append(f"gate_decision not allowed: {gate_decision} not in {sorted(allowed_gate_decisions)}")

    risk_violations = risk.get("violations")
    risk_violation_count = len(risk_violations) if isinstance(risk_violations, list) else 0
    risk_warnings = risk.get("warnings")
    risk_warning_count = len(risk_warnings) if isinstance(risk_warnings, list) else 0

    max_violation_count = int(to_float(profile.get("max_violation_count", 0), 0))
    max_warning_count = int(to_float(profile.get("max_warning_count", 0), 0))
    if risk_violation_count > max(0, max_violation_count):
        violations.append(
            f"risk violation count exceeded: {risk_violation_count} > max_violation_count={max(0, max_violation_count)}"
        )
    if risk_warning_count > max(0, max_warning_count):
        violations.append(
            f"risk warning count exceeded: {risk_warning_count} > max_warning_count={max(0, max_warning_count)}"
        )

    override_active = bool(risk.get("override_active", False))
    override_mode = str(risk.get("override_mode", "") or "").strip().lower()
    allowed_override_modes = {
        str(item).strip().lower()
        for item in (profile.get("allowed_override_modes") or [])
        if str(item).strip()
    }
    if override_active:
        if not override_mode:
            violations.append("override_active=true but override_mode is empty")
        elif override_mode not in allowed_override_modes:
            violations.append(
                f"override mode not allowed for profile {args.profile}: {override_mode} not in {sorted(allowed_override_modes)}"
            )

    freshness = profile.get("freshness")
    if isinstance(freshness, dict):
        risk_generated_at = parse_iso_dt(risk.get("generated_at"))
        check_freshness(
            generated_at=risk_generated_at,
            max_age_hours=to_float(freshness.get("max_risk_note_age_hours", 72.0), 72.0),
            label="risk_note",
            violations=violations,
            warnings=warnings,
            strict=bool(args.strict),
        )

        failover_generated_at = parse_iso_dt(failover.get("generated_at"))
        check_freshness(
            generated_at=failover_generated_at,
            max_age_hours=to_float(freshness.get("max_failover_status_age_hours", 72.0), 72.0),
            label="failover_status",
            violations=violations,
            warnings=warnings,
            strict=bool(args.strict),
        )

    route = profile.get("route")
    if isinstance(route, dict):
        stats = risk.get("latest_route_stats")
        if isinstance(stats, dict):
            route_success = to_float(stats.get("route_success_rate"), 0.0)
            route_timeout = to_float(stats.get("route_timeout_rate"), 0.0)
            min_route_success = to_float(route.get("min_route_success_rate"), 0.0)
            max_route_timeout = to_float(route.get("max_route_timeout_rate"), 1.0)
            if route_success < min_route_success:
                violations.append(
                    f"route_success_rate too low: {route_success:.4f} < min_route_success_rate={min_route_success:.4f}"
                )
            if route_timeout > max_route_timeout:
                violations.append(
                    f"route_timeout_rate too high: {route_timeout:.4f} > max_route_timeout_rate={max_route_timeout:.4f}"
                )

    latency = profile.get("latency")
    if isinstance(latency, dict):
        metrics = risk.get("latest_metrics")
        if isinstance(metrics, dict):
            latency_p95 = to_float(metrics.get("latency_p95_ms"), 0.0)
            max_latency = to_float(latency.get("max_latency_p95_ms"), 999999.0)
            if latency_p95 > max_latency:
                violations.append(f"latency_p95_ms too high: {latency_p95:.2f} > max_latency_p95_ms={max_latency:.2f}")

    failover_policy = profile.get("failover")
    if isinstance(failover_policy, dict):
        latest = failover.get("latest")
        if isinstance(latest, dict):
            latest_result = str(latest.get("result", "") or "").strip().lower()
            allowed_latest_results = {
                str(item).strip().lower()
                for item in (failover_policy.get("allowed_latest_results") or [])
                if str(item).strip()
            }
            if latest_result and allowed_latest_results and latest_result not in allowed_latest_results:
                violations.append(
                    f"failover latest result not allowed: {latest_result} not in {sorted(allowed_latest_results)}"
                )
            latest_timeout_ratio = to_float(latest.get("timeout_error_ratio"), 0.0)
            max_latest_timeout_ratio = to_float(failover_policy.get("max_latest_timeout_error_ratio"), 1.0)
            if latest_timeout_ratio > max_latest_timeout_ratio:
                violations.append(
                    "failover latest timeout ratio too high: "
                    f"{latest_timeout_ratio:.4f} > max_latest_timeout_error_ratio={max_latest_timeout_ratio:.4f}"
                )

        window_counts = failover.get("window_counts")
        if isinstance(window_counts, dict):
            fail_window_count = int(to_float(window_counts.get("fail"), 0))
            max_fail_window = int(to_float(failover_policy.get("max_fail_window"), 999))
            if fail_window_count > max_fail_window:
                violations.append(f"failover window fail count exceeded: {fail_window_count} > max_fail_window={max_fail_window}")

        recent_runs = failover.get("recent_runs")
        if isinstance(recent_runs, list):
            typed_recent = [item for item in recent_runs if isinstance(item, dict)]
            fail_streak = count_latest_fail_streak(typed_recent)
            max_fail_streak = int(to_float(failover_policy.get("max_fail_streak"), 999))
            if fail_streak > max_fail_streak:
                violations.append(f"failover fail streak exceeded: {fail_streak} > max_fail_streak={max_fail_streak}")

    status = "PASS" if not violations else "BLOCK"
    payload = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "profile": args.profile,
        "policy_path": str(policy_path),
        "risk_note_path": str(risk_path),
        "failover_status_path": str(failover_path),
        "strict": bool(args.strict),
        "status": status,
        "violations": violations,
        "warnings": warnings,
        "risk_gate_decision": gate_decision,
        "risk_violation_count": risk_violation_count,
        "risk_warning_count": risk_warning_count,
        "override_active": override_active,
        "override_mode": override_mode,
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Release Policy Check",
        "",
        f"- Generated: `{payload['generated_at']}`",
        f"- Profile: `{args.profile}`",
        f"- Status: `{status}`",
        f"- Strict: `{bool(args.strict)}`",
        "",
        "## Snapshot",
        f"- gate_decision: `{gate_decision}`",
        f"- risk violations: `{risk_violation_count}`",
        f"- risk warnings: `{risk_warning_count}`",
        f"- override: `active={override_active}, mode={override_mode}`",
        "",
        "## Violations",
    ]
    if violations:
        md_lines.extend([f"- {item}" for item in violations])
    else:
        md_lines.append("- none")
    md_lines.extend(["", "## Warnings"])
    if warnings:
        md_lines.extend([f"- {item}" for item in warnings])
    else:
        md_lines.append("- none")
    md_lines.extend(
        [
            "",
            "## Files",
            f"- policy: `{policy_path}`",
            f"- risk note: `{risk_path}`",
            f"- failover status: `{failover_path}`",
            f"- output json: `{output_json}`",
        ]
    )
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    if not args.quiet:
        print(f"release policy check [{args.profile}] -> {status}")
        print(f"- output json: {output_json}")
        print(f"- output md: {output_md}")
        if violations:
            for item in violations:
                print(f"- violation: {item}")
        if warnings:
            for item in warnings:
                print(f"- warning: {item}")

    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

