#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate failover status summary for ops dashboard/gate.")
    parser.add_argument("--repo-root", default=".", help="Repository root.")
    parser.add_argument(
        "--reports-root",
        default="artifacts/model_failover_eval",
        help="Root directory that contains run_*/model_failover_report.json",
    )
    parser.add_argument(
        "--output-json",
        default="docs/eval/failover_status.json",
        help="Output json path.",
    )
    parser.add_argument(
        "--output-md",
        default="docs/eval/failover_status.md",
        help="Output markdown path.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Rolling window in days for summary.",
    )
    return parser.parse_args()


def parse_iso_dt(value: str) -> datetime | None:
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        return datetime.fromisoformat(raw).astimezone(timezone.utc)
    except ValueError:
        return None


def resolve_path(repo_root: Path, raw: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = repo_root / path
    return path.resolve()


def infer_result(payload: dict[str, Any]) -> str:
    explicit = str(payload.get("result", "") or "").strip().lower()
    if explicit in {"pass", "degraded", "fail"}:
        return explicit

    runs = payload.get("runs", {}) or {}
    primary = runs.get("primary", {}) or {}
    fallback = runs.get("fallback", {}) or {}
    failover_triggered = bool(payload.get("failover_triggered", False))

    if fallback:
        exit_code = int(fallback.get("exit_code", 1) or 1)
        fetch_errors = int(fallback.get("fetch_error_count", 0) or 0)
        if exit_code != 0:
            return "fail"
        return "pass" if fetch_errors == 0 else "degraded"

    if primary:
        exit_code = int(primary.get("exit_code", 1) or 1)
        fetch_errors = int(primary.get("fetch_error_count", 0) or 0)
        if exit_code != 0:
            return "fail"
        if failover_triggered:
            return "fail"
        return "pass" if fetch_errors == 0 else "degraded"

    return "fail"


def load_reports(reports_root: Path) -> list[dict[str, Any]]:
    if not reports_root.exists():
        return []
    rows: list[dict[str, Any]] = []
    for report_path in reports_root.glob("run_*/model_failover_report.json"):
        try:
            payload = json.loads(report_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        generated_at = parse_iso_dt(str(payload.get("generated_at", "") or ""))
        if generated_at is None:
            continue
        result = infer_result(payload)
        runs = payload.get("runs", {}) or {}
        final_run = runs.get("fallback", {}) or runs.get("primary", {}) or {}
        row = {
            "path": str(report_path),
            "generated_at": generated_at.isoformat(timespec="seconds"),
            "result": result,
            "failover_triggered": bool(payload.get("failover_triggered", False)),
            "failover_reason": str(payload.get("failover_reason", "") or "").strip(),
            "active_model_final": str(payload.get("active_model_final", "") or "").strip(),
            "fetch_error_count": int(final_run.get("fetch_error_count", 0) or 0),
            "timeout_error_ratio": float(final_run.get("timeout_error_ratio", 0.0) or 0.0),
        }
        rows.append(row)
    rows.sort(key=lambda item: item["generated_at"])
    return rows


def build_summary(rows: list[dict[str, Any]], *, days: int) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=max(1, int(days)))
    window_rows = [item for item in rows if parse_iso_dt(str(item.get("generated_at", ""))) and parse_iso_dt(str(item.get("generated_at", ""))) >= window_start]

    def _count(result: str) -> int:
        return sum(1 for item in window_rows if item.get("result") == result)

    latest = rows[-1] if rows else None
    return {
        "generated_at": now.isoformat(timespec="seconds"),
        "window_days": max(1, int(days)),
        "total_runs_all_time": len(rows),
        "total_runs_window": len(window_rows),
        "window_counts": {
            "pass": _count("pass"),
            "degraded": _count("degraded"),
            "fail": _count("fail"),
            "failover_triggered": sum(1 for item in window_rows if item.get("failover_triggered")),
        },
        "latest": latest,
        "recent_runs": window_rows[-20:],
    }


def render_markdown(summary: dict[str, Any]) -> str:
    latest = summary.get("latest") or {}
    lines: list[str] = []
    lines.append("# Failover Status")
    lines.append("")
    lines.append(f"- Generated At: `{summary.get('generated_at', '')}`")
    lines.append(f"- Window Days: `{summary.get('window_days', 0)}`")
    lines.append(f"- Total Runs (All): `{summary.get('total_runs_all_time', 0)}`")
    lines.append(f"- Total Runs (Window): `{summary.get('total_runs_window', 0)}`")
    lines.append("")
    lines.append("## Window Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    counts = summary.get("window_counts", {}) or {}
    lines.append(f"| PASS | {counts.get('pass', 0)} |")
    lines.append(f"| DEGRADED | {counts.get('degraded', 0)} |")
    lines.append(f"| FAIL | {counts.get('fail', 0)} |")
    lines.append(f"| Failover Triggered | {counts.get('failover_triggered', 0)} |")
    lines.append("")
    lines.append("## Latest")
    lines.append("")
    if latest:
        lines.append(f"- Result: `{latest.get('result', 'unknown')}`")
        lines.append(f"- Generated At: `{latest.get('generated_at', '')}`")
        lines.append(f"- Final Model: `{latest.get('active_model_final', '')}`")
        lines.append(f"- Failover Triggered: `{latest.get('failover_triggered', False)}`")
        lines.append(f"- Failover Reason: `{latest.get('failover_reason', '')}`")
        lines.append(f"- Fetch Error Count: `{latest.get('fetch_error_count', 0)}`")
        lines.append(f"- Timeout Error Ratio: `{latest.get('timeout_error_ratio', 0.0):.4f}`")
        lines.append(f"- Report Path: `{latest.get('path', '')}`")
    else:
        lines.append("- No failover reports found.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    reports_root = resolve_path(repo_root, args.reports_root)
    output_json = resolve_path(repo_root, args.output_json)
    output_md = resolve_path(repo_root, args.output_md)

    rows = load_reports(reports_root)
    summary = build_summary(rows, days=max(1, int(args.days)))

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md.write_text(render_markdown(summary), encoding="utf-8")

    print(f"Generated failover status json: {output_json}")
    print(f"Generated failover status md: {output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
