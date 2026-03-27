#!/usr/bin/env python3
"""
Validate one-click AI pipeline report thresholds.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate ai_oneclick_report.json gate.")
    parser.add_argument(
        "--report",
        required=True,
        help="Path to ai_oneclick_report.json",
    )
    parser.add_argument(
        "--min-audit-pass-rate",
        type=float,
        default=0.25,
        help="Minimum acceptable audit pass rate.",
    )
    parser.add_argument(
        "--min-recheck-pass-rate",
        type=float,
        default=0.15,
        help="Minimum acceptable recheck pass rate.",
    )
    parser.add_argument(
        "--max-audit-parse-error-rate",
        type=float,
        default=0.2,
        help="Maximum acceptable audit parse error rate.",
    )
    parser.add_argument(
        "--max-audit-call-error-rate",
        type=float,
        default=0.2,
        help="Maximum acceptable audit upstream call error rate.",
    )
    parser.add_argument(
        "--require-merge-appended",
        action="store_true",
        help="Require merge appended_rows >= 1.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report_path = Path(args.report).resolve()
    if not report_path.exists():
        raise SystemExit(f"Report not found: {report_path}")

    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON report: {report_path} ({exc})") from exc

    errors: list[str] = []

    if report.get("status") != "success":
        errors.append(f"pipeline status is not success: {report.get('status')}")

    counts = report.get("counts", {}) if isinstance(report.get("counts"), dict) else {}
    candidate_rows = int(counts.get("candidate_rows", 0) or 0)
    audit_pass_rows = int(counts.get("audit_pass_rows", 0) or 0)
    recheck_pass_rows = int(counts.get("recheck_pass_rows", 0) or 0)

    audit_pass_rate = (audit_pass_rows / candidate_rows) if candidate_rows else 0.0
    recheck_pass_rate = (recheck_pass_rows / candidate_rows) if candidate_rows else 0.0

    if audit_pass_rate < args.min_audit_pass_rate:
        errors.append(
            f"audit pass rate too low: {audit_pass_rate:.3f} < {args.min_audit_pass_rate:.3f}"
        )
    if recheck_pass_rate < args.min_recheck_pass_rate:
        errors.append(
            f"recheck pass rate too low: {recheck_pass_rate:.3f} < {args.min_recheck_pass_rate:.3f}"
        )

    ai = report.get("ai", {}) if isinstance(report.get("ai"), dict) else {}
    audit = ai.get("audit", {}) if isinstance(ai.get("audit"), dict) else {}
    parse_error_rate = float(audit.get("parse_error_rate", 0.0) or 0.0)
    call_error_rate = float(audit.get("call_error_rate", 0.0) or 0.0)
    if parse_error_rate > args.max_audit_parse_error_rate:
        errors.append(
            f"audit parse error rate too high: {parse_error_rate:.3f} > {args.max_audit_parse_error_rate:.3f}"
        )
    if call_error_rate > args.max_audit_call_error_rate:
        errors.append(
            f"audit call error rate too high: {call_error_rate:.3f} > {args.max_audit_call_error_rate:.3f}"
        )

    if args.require_merge_appended:
        merge_stat = (
            report.get("merge_stat", {}) if isinstance(report.get("merge_stat"), dict) else {}
        )
        appended = int(merge_stat.get("appended_rows", 0) or 0)
        if appended < 1:
            errors.append("require-merge-appended enabled, but appended_rows < 1")

    if errors:
        print("AI pipeline gate failed:")
        for item in errors:
            print(f"- {item}")
        return 1

    print("AI pipeline gate passed.")
    print(f"- candidate_rows={candidate_rows}")
    print(f"- audit_pass_rows={audit_pass_rows} (rate={audit_pass_rate:.3f})")
    print(f"- recheck_pass_rows={recheck_pass_rows} (rate={recheck_pass_rate:.3f})")
    print(f"- audit_call_error_rate={call_error_rate:.3f}")
    print(f"- audit_parse_error_rate={parse_error_rate:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
