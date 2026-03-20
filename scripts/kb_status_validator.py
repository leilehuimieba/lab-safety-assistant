#!/usr/bin/env python3
"""
Knowledge Base Status State Machine Validator

This script validates the KB status lifecycle and ensures proper state transitions.

Lifecycle States:
    draft -> pending_review -> approved -> active -> deprecated
                            |
                            v
                         rejected

Valid Transitions:
    draft -> pending_review (when traceability info is complete)
    pending_review -> approved (after review)
    pending_review -> rejected (review failed)
    approved -> active (when published)
    active -> deprecated (when replaced or obsolete)
    rejected -> pending_review (re-submission after fix)

Usage:
    python kb_status_validator.py [command]

Commands:
    report     - Show status distribution and transition analysis
    validate   - Check for invalid transitions
    stats      - Show detailed statistics
"""

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional


VALID_STATUSES = {
    "draft",           # Initial state, traceability incomplete
    "pending_review",  # Ready for review
    "approved",       # Reviewed and approved
    "rejected",       # Review failed
    "active",         # Published and in use
    "deprecated",     # No longer in use
}

VALID_TRANSITIONS = {
    "draft": {"pending_review", "rejected"},
    "pending_review": {"approved", "rejected", "draft"},
    "approved": {"active", "rejected"},
    "rejected": {"pending_review", "draft"},
    "active": {"deprecated"},
    "deprecated": set(),  # Terminal state
}

STATUS_DESCRIPTIONS = {
    "draft": "Initial state - traceability info incomplete",
    "pending_review": "Ready for review - awaiting reviewer approval",
    "approved": "Reviewed and approved - ready to be published",
    "rejected": "Review failed - needs revision",
    "active": "Published and in use",
    "deprecated": "No longer in use - replaced or obsolete",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="KB Status State Machine Validator"
    )
    parser.add_argument(
        "--kb-path",
        type=Path,
        default=Path("knowledge_base_curated.csv"),
        help="Path to knowledge base CSV file",
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    subparsers.add_parser("report", help="Show status distribution")
    subparsers.add_parser("validate", help="Validate state transitions")
    subparsers.add_parser("stats", help="Show detailed statistics")

    return parser.parse_args()


def load_kb(kb_path: Path) -> tuple[list[dict], dict]:
    with kb_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    return rows, reader.fieldnames or []


def analyze_status(rows: list[dict]) -> dict:
    status_counts = defaultdict(int)
    entries_by_status = defaultdict(list)

    for row in rows:
        status = row.get("status", "unknown")
        status_counts[status] += 1
        entries_by_status[status].append(row.get("id", "unknown"))

    return {
        "counts": dict(status_counts),
        "entries": {k: list(v) for k, v in entries_by_status.items()},
    }


def validate_transitions(rows: list[dict]) -> tuple[bool, list[str]]:
    errors = []
    id_to_status = {row.get("id", ""): row.get("status", "") for row in rows}

    for row in rows:
        entry_id = row.get("id", f"row_{rows.index(row)}")
        status = row.get("status", "")

        if status not in VALID_STATUSES:
            errors.append(
                f"{entry_id}: Invalid status '{status}'. "
                f"Valid statuses: {', '.join(sorted(VALID_STATUSES))}"
            )

    if errors:
        return False, errors
    return True, []


def check_traceability_complete(row: dict) -> bool:
    required_fields = ["source_type", "source_title", "source_org", "source_date"]
    for field in required_fields:
        value = row.get(field, "")
        if not value or value in ["待补充", ""]:
            return False
    return True


def report_status(rows: list[dict]) -> None:
    analysis = analyze_status(rows)

    print("=" * 60)
    print("Knowledge Base Status Report")
    print("=" * 60)
    print(f"\nTotal entries: {len(rows)}")
    print(f"Unique statuses: {len(analysis['counts'])}")
    print()

    print("Status Distribution:")
    print("-" * 40)
    for status, count in sorted(analysis["counts"].items()):
        desc = STATUS_DESCRIPTIONS.get(status, "Unknown")
        pct = 100 * count / len(rows) if rows else 0
        print(f"  {status:20} {count:4} ({pct:5.1f}%) - {desc}")

    print()
    print("Valid Transitions:")
    print("-" * 40)
    for from_status, to_statuses in sorted(VALID_TRANSITIONS.items()):
        if to_statuses:
            print(f"  {from_status} -> {', '.join(sorted(to_statuses))}")
        else:
            print(f"  {from_status} -> (terminal)")

    print()
    print("Traceability Completeness by Status:")
    print("-" * 40)
    for status, entries in analysis["entries"].items():
        complete = sum(
            1 for eid in entries
            if check_traceability_complete(
                next((r for r in rows if r.get("id") == eid), {})
            )
        )
        total = len(entries)
        pct = 100 * complete / total if total > 0 else 0
        print(f"  {status}: {complete}/{total} ({pct:.1f}%) with complete traceability")


def validate(rows: list[dict]) -> int:
    is_valid, errors = validate_transitions(rows)

    if is_valid:
        print("Status validation passed")
        return 0
    else:
        print("Status validation failed:")
        for err in errors:
            print(f"  - {err}")
        return 1


def stats(rows: list[dict]) -> None:
    analysis = analyze_status(rows)

    print("=" * 60)
    print("Knowledge Base Detailed Statistics")
    print("=" * 60)

    print("\nStatus Distribution:")
    for status, count in sorted(analysis["counts"].items()):
        entries = analysis["entries"][status]
        print(f"\n  {status} ({count} entries):")
        for eid in entries[:5]:
            print(f"    - {eid}")
        if len(entries) > 5:
            print(f"    ... and {len(entries) - 5} more")

    print("\n" + "=" * 60)
    print("Traceability Status:")
    print("=" * 60)

    complete_count = 0
    incomplete_by_status = defaultdict(list)

    for row in rows:
        if check_traceability_complete(row):
            complete_count += 1
        else:
            status = row.get("status", "unknown")
            incomplete_by_status[status].append(row.get("id", ""))

    print(f"\nTotal with complete traceability: {complete_count}/{len(rows)}")
    print("\nIncomplete by status:")
    for status, entries in sorted(incomplete_by_status.items()):
        print(f"  {status}: {len(entries)} incomplete")
        for eid in entries[:3]:
            print(f"    - {eid}")
        if len(entries) > 3:
            print(f"    ... and {len(entries) - 3} more")


def main() -> int:
    args = parse_args()
    kb_path = Path(args.kb_path).resolve()

    if not kb_path.exists():
        print(f"Error: File not found: {kb_path}", file=sys.stderr)
        return 1

    rows, _ = load_kb(kb_path)

    if not rows:
        print("Error: No rows found in KB file", file=sys.stderr)
        return 1

    if args.command == "report":
        report_status(rows)
    elif args.command == "validate":
        return validate(rows)
    elif args.command == "stats":
        stats(rows)
    else:
        report_status(rows)
        print("\nUse --help to see available commands")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
