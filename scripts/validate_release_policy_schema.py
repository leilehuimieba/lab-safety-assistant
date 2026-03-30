#!/usr/bin/env python3
"""
Validate schema of docs/eval/release_policy_v5.json.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_PROFILE_KEYS = {
    "allowed_gate_decisions",
    "max_violation_count",
    "max_warning_count",
    "allowed_override_modes",
    "freshness",
    "route",
    "latency",
    "failover",
}

ALLOWED_METRIC_RULE_KEYS = {"min", "max"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate release policy schema.")
    parser.add_argument("--repo-root", default=".", help="Repository root path.")
    parser.add_argument(
        "--policy-json",
        default="docs/eval/release_policy_v5.json",
        help="Release policy json path.",
    )
    parser.add_argument("--quiet", action="store_true", help="Print concise output.")
    return parser.parse_args()


def resolve_path(repo_root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (repo_root / path).resolve()


def is_number(value: Any) -> bool:
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True


def validate_profile(profile_name: str, profile: Any, errors: list[str]) -> None:
    if not isinstance(profile, dict):
        errors.append(f"profile {profile_name} must be object")
        return

    missing = sorted(REQUIRED_PROFILE_KEYS - set(profile.keys()))
    if missing:
        errors.append(f"profile {profile_name} missing keys: {missing}")

    for key in ("allowed_gate_decisions", "allowed_override_modes"):
        value = profile.get(key)
        if not isinstance(value, list):
            errors.append(f"profile {profile_name}.{key} must be list")

    for key in ("max_violation_count", "max_warning_count"):
        value = profile.get(key)
        if not is_number(value):
            errors.append(f"profile {profile_name}.{key} must be number")
        elif float(value) < 0:
            errors.append(f"profile {profile_name}.{key} must be >= 0")

    freshness = profile.get("freshness")
    if not isinstance(freshness, dict):
        errors.append(f"profile {profile_name}.freshness must be object")
    else:
        for key in ("max_risk_note_age_hours", "max_failover_status_age_hours"):
            value = freshness.get(key)
            if not is_number(value):
                errors.append(f"profile {profile_name}.freshness.{key} must be number")
            elif float(value) <= 0:
                errors.append(f"profile {profile_name}.freshness.{key} must be > 0")

    route = profile.get("route")
    if not isinstance(route, dict):
        errors.append(f"profile {profile_name}.route must be object")
    else:
        for key in ("min_route_success_rate", "max_route_timeout_rate"):
            value = route.get(key)
            if not is_number(value):
                errors.append(f"profile {profile_name}.route.{key} must be number")

    latency = profile.get("latency")
    if not isinstance(latency, dict):
        errors.append(f"profile {profile_name}.latency must be object")
    else:
        value = latency.get("max_latency_p95_ms")
        if not is_number(value):
            errors.append(f"profile {profile_name}.latency.max_latency_p95_ms must be number")
        elif float(value) <= 0:
            errors.append(f"profile {profile_name}.latency.max_latency_p95_ms must be > 0")

    failover = profile.get("failover")
    if not isinstance(failover, dict):
        errors.append(f"profile {profile_name}.failover must be object")
    else:
        allowed_latest_results = failover.get("allowed_latest_results")
        if not isinstance(allowed_latest_results, list) or not allowed_latest_results:
            errors.append(f"profile {profile_name}.failover.allowed_latest_results must be non-empty list")
        for key in ("max_latest_timeout_error_ratio", "max_fail_window", "max_fail_streak"):
            value = failover.get(key)
            if not is_number(value):
                errors.append(f"profile {profile_name}.failover.{key} must be number")
        ratio = failover.get("max_latest_timeout_error_ratio")
        if is_number(ratio) and not (0 <= float(ratio) <= 1):
            errors.append(f"profile {profile_name}.failover.max_latest_timeout_error_ratio must be in [0, 1]")

    metrics = profile.get("metrics")
    if metrics is not None:
        if not isinstance(metrics, dict):
            errors.append(f"profile {profile_name}.metrics must be object when present")
        else:
            for metric_name, rule in metrics.items():
                if not isinstance(rule, dict):
                    errors.append(f"profile {profile_name}.metrics.{metric_name} must be object")
                    continue
                extra = sorted(set(rule.keys()) - ALLOWED_METRIC_RULE_KEYS)
                if extra:
                    errors.append(
                        f"profile {profile_name}.metrics.{metric_name} contains unsupported keys: {extra}"
                    )
                if "min" not in rule and "max" not in rule:
                    errors.append(
                        f"profile {profile_name}.metrics.{metric_name} requires at least one of [min, max]"
                    )
                for bound in ("min", "max"):
                    if bound in rule and not is_number(rule.get(bound)):
                        errors.append(
                            f"profile {profile_name}.metrics.{metric_name}.{bound} must be number"
                        )
                min_value = rule.get("min")
                max_value = rule.get("max")
                if is_number(min_value) and is_number(max_value) and float(min_value) > float(max_value):
                    errors.append(
                        f"profile {profile_name}.metrics.{metric_name} invalid: min > max"
                    )


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    policy_path = resolve_path(repo_root, args.policy_json)

    if not policy_path.exists():
        print(f"release policy schema failed: file missing: {policy_path}")
        return 1

    try:
        payload = json.loads(policy_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"release policy schema failed: unreadable json: {exc}")
        return 1
    if not isinstance(payload, dict):
        print("release policy schema failed: root must be object")
        return 1

    errors: list[str] = []
    version = payload.get("version")
    if str(version or "").strip() == "":
        errors.append("version is required")

    profiles = payload.get("profiles")
    if not isinstance(profiles, dict):
        errors.append("profiles must be object")
    else:
        for required in ("demo", "prod"):
            if required not in profiles:
                errors.append(f"profiles missing required profile: {required}")
        for name, profile in profiles.items():
            validate_profile(str(name), profile, errors)

    if errors:
        if not args.quiet:
            print("release policy schema failed:")
            for item in errors:
                print(f"- {item}")
        else:
            print(f"release policy schema failed: {len(errors)} issue(s)")
        return 1

    if not args.quiet:
        print("release policy schema passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
