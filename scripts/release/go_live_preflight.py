#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen


@dataclass
class CheckResult:
    key: str
    ok: bool
    level: str
    detail: str


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Go-live preflight for lab-safe-assistant.")
    parser.add_argument("--repo-root", default=".", help="Repository root path.")
    parser.add_argument(
        "--release-dir",
        default="release_exports/v8.1",
        help="Release package directory to verify.",
    )
    parser.add_argument(
        "--release-oneclick-root",
        default="artifacts/eval_release_oneclick",
        help="Primary one-click report root.",
    )
    parser.add_argument(
        "--release-stability-root",
        default="artifacts/release_stability_check",
        help="Fallback stability report root (contains nested one-click reports).",
    )
    parser.add_argument(
        "--web-health-url",
        default="http://127.0.0.1:8088/health",
        help="Web demo health endpoint.",
    )
    parser.add_argument(
        "--skip-web-health",
        action="store_true",
        help="Skip web health check (not recommended for go-live).",
    )
    parser.add_argument(
        "--allow-warning-pass",
        action="store_true",
        help="Exit 0 when only warnings exist.",
    )
    parser.add_argument(
        "--enforce-prod-policy",
        action="store_true",
        default=True,
        help="Treat prod release policy as blocking gate.",
    )
    parser.add_argument(
        "--no-enforce-prod-policy",
        action="store_false",
        dest="enforce_prod_policy",
        help="Downgrade prod release policy to non-blocking info (demo drill only).",
    )
    parser.add_argument(
        "--output-json",
        default="docs/ops/go_live_readiness.json",
        help="Output JSON path.",
    )
    parser.add_argument(
        "--output-md",
        default="docs/ops/go_live_readiness.md",
        help="Output markdown path.",
    )
    return parser.parse_args()


def resolve(repo_root: Path, rel_or_abs: str) -> Path:
    path = Path(rel_or_abs)
    if path.is_absolute():
        return path
    return (repo_root / path).resolve()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def check_release_policy(path: Path, profile: str) -> CheckResult:
    payload = load_json(path)
    if not payload:
        return CheckResult(
            key=f"release_policy_{profile}",
            ok=False,
            level="blocker",
            detail=f"missing or unreadable: {path}",
        )
    status = str(payload.get("status", "")).upper()
    if status != "PASS":
        violations = payload.get("violations")
        detail = f"status={status or 'unknown'}"
        if isinstance(violations, list) and violations:
            detail += f"; violations={'; '.join(str(v) for v in violations[:3])}"
        return CheckResult(
            key=f"release_policy_{profile}",
            ok=False,
            level="blocker",
            detail=detail,
        )
    return CheckResult(
        key=f"release_policy_{profile}",
        ok=True,
        level="info",
        detail=f"status={status}",
    )


def check_override_disabled(path: Path) -> CheckResult:
    payload = load_json(path)
    if not payload:
        return CheckResult(
            key="gate_override",
            ok=False,
            level="warning",
            detail=f"missing or unreadable: {path}",
        )
    enabled = bool(payload.get("enabled", False))
    if enabled:
        return CheckResult(
            key="gate_override",
            ok=False,
            level="blocker",
            detail="override enabled=true; must disable before go-live",
        )
    return CheckResult(
        key="gate_override",
        ok=True,
        level="info",
        detail="override enabled=false",
    )


def check_risk_note(path: Path) -> CheckResult:
    payload = load_json(path)
    if not payload:
        return CheckResult(
            key="risk_note",
            ok=False,
            level="warning",
            detail=f"missing or unreadable: {path}",
        )
    gate_decision = str(payload.get("gate_decision", "")).upper()
    if gate_decision not in {"PASS", "WARN"}:
        return CheckResult(
            key="risk_note",
            ok=False,
            level="blocker",
            detail=f"gate_decision={gate_decision or 'unknown'}",
        )
    metrics = payload.get("latest_metrics") if isinstance(payload.get("latest_metrics"), dict) else {}
    emergency = float(metrics.get("emergency_pass_rate", 0.0) or 0.0)
    if emergency < 0.9:
        return CheckResult(
            key="risk_note",
            ok=False,
            level="blocker",
            detail=f"emergency_pass_rate too low: {emergency:.4f} < 0.9000",
        )
    return CheckResult(
        key="risk_note",
        ok=True,
        level="info",
        detail=f"gate_decision={gate_decision}; emergency_pass_rate={emergency:.4f}",
    )


def check_latest_release_oneclick(reports_root: Path, stability_root: Path) -> CheckResult:
    reports: list[Path] = []
    if reports_root.exists():
        reports.extend(sorted(reports_root.glob("run_*/eval_release_oneclick_report.json")))
    if stability_root.exists():
        reports.extend(sorted(stability_root.glob("run_*/round_*/run_*/eval_release_oneclick_report.json")))

    if not reports:
        return CheckResult(
            key="release_oneclick",
            ok=False,
            level="warning",
            detail=f"no oneclick report found under {reports_root} or {stability_root}",
        )

    reports = sorted(reports, key=lambda p: str(p))
    latest = reports[-1]
    payload = load_json(latest)
    status = str(payload.get("status", "")).lower()
    if status != "success":
        return CheckResult(
            key="release_oneclick",
            ok=False,
            level="blocker",
            detail=f"latest status={status or 'unknown'} ({latest})",
        )
    return CheckResult(
        key="release_oneclick",
        ok=True,
        level="info",
        detail=f"latest status=success ({latest})",
    )


def expected_prefetch_status_name(path: Path) -> str:
    release_name = path.name.strip().lower() or "v8.1"
    normalized = release_name.replace(".", "_")
    return f"web_seed_urls_{normalized}_prefetch_status.csv"


def check_release_package(path: Path) -> list[CheckResult]:
    required = [
        "knowledge_base_import_ready.csv",
        "README.md",
        expected_prefetch_status_name(path),
    ]
    results: list[CheckResult] = []
    if not path.exists():
        return [
            CheckResult(
                key="release_package",
                ok=False,
                level="blocker",
                detail=f"missing release dir: {path}",
            )
        ]
    for rel in required:
        p = path / rel
        exists = p.exists() and p.is_file()
        results.append(
            CheckResult(
                key=f"release_package::{rel}",
                ok=exists,
                level="blocker" if not exists else "info",
                detail="ok" if exists else f"missing: {p}",
            )
        )
    return results


def check_web_health(url: str, skip: bool) -> CheckResult:
    if skip:
        return CheckResult(
            key="web_health",
            ok=False,
            level="warning",
            detail="skipped by --skip-web-health",
        )
    try:
        with urlopen(url, timeout=8) as resp:  # nosec B310
            body = resp.read().decode("utf-8", errors="replace")
            code = getattr(resp, "status", 200)
    except URLError as exc:
        return CheckResult(
            key="web_health",
            ok=False,
            level="blocker",
            detail=f"{url} unreachable: {exc}",
        )
    if code >= 400:
        return CheckResult(
            key="web_health",
            ok=False,
            level="blocker",
            detail=f"http status={code}",
        )
    if '"status":"ok"' not in body.replace(" ", "") and '"status": "ok"' not in body:
        return CheckResult(
            key="web_health",
            ok=False,
            level="warning",
            detail=f"response does not include status=ok: {body[:120]}",
        )
    return CheckResult(
        key="web_health",
        ok=True,
        level="info",
        detail=f"{url} ok",
    )


def to_markdown(
    *,
    generated_at: str,
    overall: str,
    blockers: list[CheckResult],
    warnings: list[CheckResult],
    infos: list[CheckResult],
) -> str:
    lines: list[str] = []
    lines.append("# Go-Live Readiness")
    lines.append("")
    lines.append(f"- Generated: `{generated_at}`")
    lines.append(f"- Overall: `{overall}`")
    lines.append(f"- Blockers: `{len(blockers)}`")
    lines.append(f"- Warnings: `{len(warnings)}`")
    lines.append("")
    lines.append("## Blockers")
    if not blockers:
        lines.append("- none")
    else:
        for item in blockers:
            lines.append(f"- [{item.key}] {item.detail}")
    lines.append("")
    lines.append("## Warnings")
    if not warnings:
        lines.append("- none")
    else:
        for item in warnings:
            lines.append(f"- [{item.key}] {item.detail}")
    lines.append("")
    lines.append("## Info")
    for item in infos:
        lines.append(f"- [{item.key}] {item.detail}")
    lines.append("")
    lines.append("## Next Actions")
    if blockers:
        lines.append("1. Fix all blockers first, then rerun go-live preflight.")
    elif warnings:
        lines.append("1. Resolve warning items before final release.")
    else:
        lines.append("1. Ready for release window.")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()

    release_dir = resolve(repo_root, args.release_dir)
    oneclick_root = resolve(repo_root, args.release_oneclick_root)
    stability_root = resolve(repo_root, args.release_stability_root)
    output_json = resolve(repo_root, args.output_json)
    output_md = resolve(repo_root, args.output_md)

    checks: list[CheckResult] = []
    checks.extend(check_release_package(release_dir))
    checks.append(check_latest_release_oneclick(oneclick_root, stability_root))
    checks.append(check_release_policy(repo_root / "docs" / "eval" / "release_policy_check.json", "demo"))
    prod_policy_result = check_release_policy(repo_root / "docs" / "eval" / "release_policy_check_prod.json", "prod")
    if args.enforce_prod_policy:
        checks.append(prod_policy_result)
    else:
        if prod_policy_result.ok:
            checks.append(prod_policy_result)
        else:
            checks.append(
                CheckResult(
                    key="release_policy_prod",
                    ok=True,
                    level="info",
                    detail=f"{prod_policy_result.detail}; non-blocking (enforce_prod_policy=false)",
                )
            )
    checks.append(check_risk_note(repo_root / "docs" / "eval" / "release_risk_note_auto.json"))
    checks.append(check_override_disabled(repo_root / "docs" / "eval" / "eval_dashboard_gate_override.json"))
    checks.append(check_web_health(args.web_health_url.strip(), args.skip_web_health))

    blockers = [c for c in checks if c.level == "blocker" and not c.ok]
    warnings = [c for c in checks if c.level == "warning" and not c.ok]
    infos = [c for c in checks if c.ok or c.level == "info"]

    overall = "PASS"
    if blockers:
        overall = "BLOCK"
    elif warnings:
        overall = "WARN"

    payload = {
        "generated_at": now_iso(),
        "overall": overall,
        "summary": {
            "blockers": len(blockers),
            "warnings": len(warnings),
            "checks": len(checks),
        },
        "checks": [c.__dict__ for c in checks],
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md.write_text(
        to_markdown(
            generated_at=payload["generated_at"],
            overall=overall,
            blockers=blockers,
            warnings=warnings,
            infos=infos,
        ),
        encoding="utf-8",
    )

    print(f"go-live preflight overall: {overall}")
    print(f"- output json: {output_json}")
    print(f"- output md: {output_md}")

    if blockers:
        return 2
    if warnings and not args.allow_warning_pass:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
