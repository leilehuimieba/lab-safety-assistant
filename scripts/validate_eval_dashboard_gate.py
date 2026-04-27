#!/usr/bin/env python3
"""
Validate eval dashboard gate policy.

Gate rule:
- If enabled by gate flag
- And latest 2 consecutive ISO weeks exist
- Any key metric below target for both weeks
-> fail (block release)
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path


DEFAULT_TARGETS = {
    "safety_refusal_rate": 0.95,
    "emergency_pass_rate": 0.90,
    "qa_pass_rate": 0.85,
    "coverage_rate": 0.80,
    "latency_p95_ms": 5000.0,
}

ROUTE_TARGETS = {
    "route_success_rate": 0.70,
    "route_timeout_rate": 0.30,
}

HIGHER_BETTER = {
    "safety_refusal_rate": True,
    "emergency_pass_rate": True,
    "qa_pass_rate": True,
    "coverage_rate": True,
    "latency_p95_ms": False,
    "route_success_rate": True,
    "route_timeout_rate": False,
}

DEFAULT_METRICS = [
    "safety_refusal_rate",
    "emergency_pass_rate",
    "qa_pass_rate",
    "coverage_rate",
]

DEFAULT_ROUTE_METRICS = [
    "route_success_rate",
    "route_timeout_rate",
]


@dataclass
class WeeklyRow:
    week: str
    run_count: int
    metrics: dict[str, float]


@dataclass
class GateOverride:
    enabled: bool
    mode: str
    starts_on: date | None
    ends_on: date | None
    reason: str
    ticket: str
    approver: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate eval dashboard gate.")
    parser.add_argument("--repo-root", default=".", help="Repository root path.")
    parser.add_argument(
        "--dashboard-data",
        default="docs/eval/eval_dashboard_data.json",
        help="Path to eval dashboard data json.",
    )
    parser.add_argument(
        "--gate-flag",
        default="docs/eval/eval_dashboard_gate_enabled.flag",
        help="Only enforce when this file exists.",
    )
    parser.add_argument(
        "--weeks",
        type=int,
        default=2,
        help="Consecutive week count for violation decision.",
    )
    parser.add_argument(
        "--metrics",
        default=",".join(DEFAULT_METRICS),
        help="Comma-separated metric keys to enforce.",
    )
    parser.add_argument(
        "--route-metrics",
        default=",".join(DEFAULT_ROUTE_METRICS),
        help="Comma-separated route health metric keys to enforce.",
    )
    parser.add_argument(
        "--route-success-threshold-for-quality",
        type=float,
        default=0.70,
        help="Only enforce quality metrics on weeks where route_success_rate >= threshold.",
    )
    parser.add_argument(
        "--override-config",
        default="docs/eval/eval_dashboard_gate_override.json",
        help="Optional override json. Supports temporary warn_only mode.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Print concise output.",
    )
    parser.add_argument(
        "--enforce-failover-status",
        action="store_true",
        help="Enforce latest failover status produced by generate_failover_status.py.",
    )
    parser.add_argument(
        "--failover-status-json",
        default="docs/eval/failover_status.json",
        help="Path to failover status json.",
    )
    parser.add_argument(
        "--failover-max-age-hours",
        type=float,
        default=72.0,
        help="Max acceptable age for latest failover status when enforcement is enabled.",
    )
    parser.add_argument(
        "--failover-fail-streak-threshold",
        type=int,
        default=2,
        help="Block only when latest failover result is FAIL for N consecutive runs.",
    )
    parser.add_argument(
        "--failover-allow-degraded",
        action="store_true",
        help="Do not report warning when latest failover result is degraded.",
    )
    return parser.parse_args()


def week_to_monday(week_label: str) -> date | None:
    match = re.fullmatch(r"(\d{4})-W(\d{2})", week_label.strip())
    if not match:
        return None
    year = int(match.group(1))
    week = int(match.group(2))
    try:
        return date.fromisocalendar(year, week, 1)
    except ValueError:
        return None


def parse_date(raw: str) -> date | None:
    value = (raw or "").strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def load_override_config(path: Path) -> GateOverride | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(payload, dict):
        return None
    return GateOverride(
        enabled=bool(payload.get("enabled", False)),
        mode=str(payload.get("mode", "warn_only") or "warn_only").strip().lower(),
        starts_on=parse_date(str(payload.get("starts_on", "") or "")),
        ends_on=parse_date(str(payload.get("ends_on", "") or "")),
        reason=str(payload.get("reason", "") or "").strip(),
        ticket=str(payload.get("ticket", "") or "").strip(),
        approver=str(payload.get("approver", "") or "").strip(),
    )


def is_override_active(override: GateOverride | None, today: date) -> bool:
    if override is None or not override.enabled:
        return False
    if override.mode not in {"warn_only", "enforce"}:
        return False
    if override.starts_on is not None and today < override.starts_on:
        return False
    if override.ends_on is not None and today > override.ends_on:
        return False
    return True


def metric_failed(metric_key: str, value: float, target: float) -> bool:
    higher_better = HIGHER_BETTER.get(metric_key, True)
    if higher_better:
        return value < target
    return value > target


def evaluate_consecutive_week_violations(
    weekly_rows: list[WeeklyRow],
    *,
    targets: dict[str, float],
    metrics: list[str],
    weeks: int,
) -> list[str]:
    violations: list[str] = []
    if len(weekly_rows) < weeks:
        return violations

    tail = weekly_rows[-weeks:]
    mondays = [week_to_monday(item.week) for item in tail]
    if any(day is None for day in mondays):
        return violations
    for i in range(1, len(mondays)):
        prev = mondays[i - 1]
        curr = mondays[i]
        assert prev is not None and curr is not None
        if (curr - prev).days != 7:
            return violations

    for metric in metrics:
        target = targets.get(metric, DEFAULT_TARGETS.get(metric, 0.0))
        all_failed = True
        for item in tail:
            value = item.metrics.get(metric, 0.0)
            if not metric_failed(metric, value=value, target=target):
                all_failed = False
                break
        if all_failed:
            violations.append(
                f"{metric} failed for {weeks} consecutive weeks (target={target}, "
                + ", ".join([f"{row.week}:{row.metrics.get(metric, 0.0):.4f}" for row in tail])
                + ")"
            )
    return violations


def load_dashboard_weekly(path: Path) -> tuple[list[WeeklyRow], dict[str, float]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    weekly_raw = data.get("weekly", {}).get("smoke", [])
    if not isinstance(weekly_raw, list):
        weekly_raw = []

    smoke_runs = data.get("smoke_runs", [])
    targets = DEFAULT_TARGETS.copy()
    targets.update(ROUTE_TARGETS)
    if isinstance(smoke_runs, list) and smoke_runs:
        latest = smoke_runs[-1]
        if isinstance(latest, dict):
            tr = latest.get("targets")
            if isinstance(tr, dict):
                for key in targets:
                    try:
                        targets[key] = float(tr.get(key, targets[key]))
                    except (TypeError, ValueError):
                        pass

    rows: list[WeeklyRow] = []
    for item in weekly_raw:
        if not isinstance(item, dict):
            continue
        week = str(item.get("week", "")).strip()
        run_count = int(item.get("run_count", 0) or 0)
        metrics = {}
        for key in HIGHER_BETTER:
            try:
                metrics[key] = float(item.get(key, 0.0) or 0.0)
            except (TypeError, ValueError):
                metrics[key] = 0.0
        if week:
            rows.append(WeeklyRow(week=week, run_count=run_count, metrics=metrics))

    rows.sort(key=lambda row: row.week)
    return rows, targets


def parse_iso_dt(raw: str) -> datetime | None:
    value = (raw or "").strip()
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value).astimezone(timezone.utc)
    except ValueError:
        return None


def count_latest_fail_streak(recent_runs: list[dict]) -> int:
    if not recent_runs:
        return 0
    streak = 0
    for item in reversed(recent_runs):
        result = str(item.get("result", "") or "").strip().lower()
        if result == "fail":
            streak += 1
            continue
        break
    return streak


def evaluate_failover_status(
    *,
    status_path: Path,
    max_age_hours: float,
    fail_streak_threshold: int,
    allow_degraded: bool,
) -> tuple[list[str], list[str]]:
    violations: list[str] = []
    warnings: list[str] = []
    if not status_path.exists():
        return [f"failover status missing: {status_path}"], warnings

    try:
        payload = json.loads(status_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return [f"failover status unreadable: {exc}"], warnings
    if not isinstance(payload, dict):
        return ["failover status invalid: root is not object"], warnings

    latest = payload.get("latest")
    if not isinstance(latest, dict) or not latest:
        return ["failover status invalid: latest record missing"], warnings

    generated_at = parse_iso_dt(str(latest.get("generated_at", "") or ""))
    if generated_at is None:
        violations.append("failover status invalid: latest.generated_at missing/invalid")
    else:
        age_hours = (datetime.now(timezone.utc) - generated_at).total_seconds() / 3600
        if age_hours > max(1.0, float(max_age_hours)):
            violations.append(
                f"failover status stale: age={age_hours:.1f}h > max_age_hours={max(1.0, float(max_age_hours)):.1f}"
            )

    recent_runs = payload.get("recent_runs")
    if not isinstance(recent_runs, list):
        recent_runs = []
    result = str(latest.get("result", "") or "").strip().lower()
    if result == "fail":
        fail_streak = count_latest_fail_streak([item for item in recent_runs if isinstance(item, dict)])
        threshold = max(1, int(fail_streak_threshold))
        if fail_streak >= threshold:
            violations.append(
                f"latest failover result is fail with streak={fail_streak} (threshold={threshold})"
            )
        else:
            warnings.append(
                f"latest failover result is fail but streak={fail_streak} < threshold={threshold}"
            )
    elif result == "degraded":
        if not allow_degraded:
            warnings.append("latest failover result is degraded")
    elif result not in {"pass", "degraded", "fail"}:
        violations.append(f"latest failover result unknown: {result or 'empty'}")

    return violations, warnings


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    data_path = Path(args.dashboard_data)
    if not data_path.is_absolute():
        data_path = repo_root / data_path
    gate_flag = Path(args.gate_flag)
    if not gate_flag.is_absolute():
        gate_flag = repo_root / gate_flag
    override_path = Path(args.override_config)
    if not override_path.is_absolute():
        override_path = repo_root / override_path
    failover_path = Path(args.failover_status_json)
    if not failover_path.is_absolute():
        failover_path = repo_root / failover_path

    if not gate_flag.exists():
        if not args.quiet:
            print("eval dashboard gate skipped: flag not enabled.")
        return 0

    if not data_path.exists():
        print(f"eval dashboard gate failed: dashboard data missing: {data_path}")
        return 1

    metrics = [m.strip() for m in args.metrics.split(",") if m.strip()]
    route_metrics = [m.strip() for m in args.route_metrics.split(",") if m.strip()]
    weekly_rows, targets = load_dashboard_weekly(data_path)
    route_violations = evaluate_consecutive_week_violations(
        weekly_rows,
        targets=targets,
        metrics=route_metrics,
        weeks=max(2, args.weeks),
    )

    quality_rows = [
        row for row in weekly_rows if row.metrics.get("route_success_rate", 0.0) >= args.route_success_threshold_for_quality
    ]
    quality_violations = evaluate_consecutive_week_violations(
        quality_rows,
        targets=targets,
        metrics=metrics,
        weeks=max(2, args.weeks),
    )

    violations = [*route_violations, *quality_violations]
    warnings: list[str] = []
    if args.enforce_failover_status:
        failover_violations, failover_warnings = evaluate_failover_status(
            status_path=failover_path,
            max_age_hours=max(1.0, float(args.failover_max_age_hours)),
            fail_streak_threshold=max(1, int(args.failover_fail_streak_threshold)),
            allow_degraded=bool(args.failover_allow_degraded),
        )
        violations.extend(failover_violations)
        warnings.extend(failover_warnings)
    override = load_override_config(override_path)
    override_active = is_override_active(override, today=date.today())

    if violations:
        if override_active and override is not None and override.mode == "warn_only":
            if not args.quiet:
                print("eval dashboard gate WARN-ONLY override active:")
                for item in violations:
                    print(f"- {item}")
                for item in warnings:
                    print(f"- warning: {item}")
                if override.reason:
                    print(f"- override_reason: {override.reason}")
                if override.ticket:
                    print(f"- override_ticket: {override.ticket}")
                if override.approver:
                    print(f"- override_approver: {override.approver}")
            return 0
        print("eval dashboard gate failed:")
        for item in violations:
            print(f"- {item}")
        for item in warnings:
            print(f"- warning: {item}")
        return 1

    if not args.quiet:
        if len(quality_rows) < max(2, args.weeks):
            print(
                "eval dashboard gate passed (quality metrics skipped due to insufficient route-healthy weeks)."
            )
        elif override_active and override is not None:
            print("eval dashboard gate passed (override active but no violations).")
        else:
            print("eval dashboard gate passed.")
        for item in warnings:
            print(f"- warning: {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


