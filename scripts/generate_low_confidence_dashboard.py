#!/usr/bin/env python3
"""
Generate low-confidence queue dashboard from follow-up queue CSV.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


OPEN_STATUSES = {"open", "todo", "pending", "new"}
CLOSED_STATUSES = {"closed", "done", "resolved"}


@dataclass
class QueueRow:
    created_at: datetime | None
    mode: str
    status: str
    decision: str
    reason: str
    suggested_lane: str
    top_source_title: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate low-confidence queue dashboard.")
    parser.add_argument("--repo-root", default=".", help="Repository root path.")
    parser.add_argument(
        "--queue-csv",
        default="artifacts/low_confidence_followups/data_gap_queue.csv",
        help="Low-confidence queue csv path.",
    )
    parser.add_argument(
        "--stale-days",
        type=int,
        default=7,
        help="Mark open items older than this threshold as stale.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=10,
        help="Top-N size for breakdown sections.",
    )
    parser.add_argument(
        "--output-json",
        default="docs/eval/low_confidence_dashboard.json",
        help="Output json path.",
    )
    parser.add_argument(
        "--output-md",
        default="docs/eval/low_confidence_dashboard.md",
        help="Output markdown path.",
    )
    return parser.parse_args()


def resolve_path(repo_root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (repo_root / path).resolve()


def parse_dt(value: str) -> datetime | None:
    text = (value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def normalize_reason(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return "unknown"
    # Keep reason root for stable clustering: `a|b|c` -> `a`
    return text.split("|", 1)[0].strip() or "unknown"


def load_rows(path: Path) -> list[QueueRow]:
    if not path.exists():
        return []
    out: list[QueueRow] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            out.append(
                QueueRow(
                    created_at=parse_dt(row.get("created_at", "")),
                    mode=(row.get("mode") or "").strip().lower() or "unknown",
                    status=(row.get("status") or "").strip().lower() or "unknown",
                    decision=(row.get("decision") or "").strip().lower() or "unknown",
                    reason=normalize_reason(row.get("low_confidence_reason") or ""),
                    suggested_lane=(row.get("suggested_lane") or "").strip().lower() or "unknown",
                    top_source_title=(row.get("top_source_title") or "").strip() or "unknown",
                )
            )
    return out


def counter_to_top(counter: Counter[str], top_n: int) -> list[dict[str, Any]]:
    return [{"name": key, "count": int(value)} for key, value in counter.most_common(max(1, top_n))]


def build_dashboard(rows: list[QueueRow], stale_days: int, top_n: int, queue_path: Path) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    stale_before = now - timedelta(days=max(1, int(stale_days)))

    open_count = 0
    closed_count = 0
    stale_open_count = 0
    latest_created: datetime | None = None

    by_mode: Counter[str] = Counter()
    by_status: Counter[str] = Counter()
    by_decision: Counter[str] = Counter()
    by_reason: Counter[str] = Counter()
    by_lane: Counter[str] = Counter()
    by_source: Counter[str] = Counter()

    for item in rows:
        by_mode[item.mode] += 1
        by_status[item.status] += 1
        by_decision[item.decision] += 1
        by_reason[item.reason] += 1
        by_lane[item.suggested_lane] += 1
        by_source[item.top_source_title] += 1

        if item.created_at is not None:
            if latest_created is None or item.created_at > latest_created:
                latest_created = item.created_at

        if item.status in OPEN_STATUSES:
            open_count += 1
            if item.created_at is not None and item.created_at <= stale_before:
                stale_open_count += 1
        elif item.status in CLOSED_STATUSES:
            closed_count += 1

    payload: dict[str, Any] = {
        "generated_at": now.astimezone().isoformat(timespec="seconds"),
        "queue_csv": str(queue_path),
        "total": len(rows),
        "open": open_count,
        "closed": closed_count,
        "other": max(0, len(rows) - open_count - closed_count),
        "stale_days_threshold": max(1, int(stale_days)),
        "stale_open": stale_open_count,
        "latest_created_at": latest_created.astimezone().isoformat(timespec="seconds") if latest_created else "",
        "top_mode": counter_to_top(by_mode, top_n),
        "top_status": counter_to_top(by_status, top_n),
        "top_decision": counter_to_top(by_decision, top_n),
        "top_reason": counter_to_top(by_reason, top_n),
        "top_suggested_lane": counter_to_top(by_lane, top_n),
        "top_source_title": counter_to_top(by_source, top_n),
    }
    return payload


def write_markdown(path: Path, payload: dict[str, Any], top_n: int) -> None:
    lines: list[str] = [
        "# Low-Confidence Queue Dashboard",
        "",
        f"- Generated: `{payload.get('generated_at', '')}`",
        f"- Queue CSV: `{payload.get('queue_csv', '')}`",
        f"- Total: `{payload.get('total', 0)}`",
        f"- Open: `{payload.get('open', 0)}`",
        f"- Closed: `{payload.get('closed', 0)}`",
        f"- Other: `{payload.get('other', 0)}`",
        f"- Stale Open (>={payload.get('stale_days_threshold', 0)}d): `{payload.get('stale_open', 0)}`",
        f"- Latest Created: `{payload.get('latest_created_at', '')}`",
        "",
        f"## Top {top_n} Reasons",
    ]
    reasons = payload.get("top_reason", [])
    if isinstance(reasons, list) and reasons:
        for item in reasons:
            if not isinstance(item, dict):
                continue
            lines.append(f"- {item.get('name', 'unknown')}: {item.get('count', 0)}")
    else:
        lines.append("- none")

    lines.append("")
    lines.append(f"## Top {top_n} Suggested Lanes")
    lanes = payload.get("top_suggested_lane", [])
    if isinstance(lanes, list) and lanes:
        for item in lanes:
            if not isinstance(item, dict):
                continue
            lines.append(f"- {item.get('name', 'unknown')}: {item.get('count', 0)}")
    else:
        lines.append("- none")

    lines.append("")
    lines.append(f"## Top {top_n} Source Titles")
    sources = payload.get("top_source_title", [])
    if isinstance(sources, list) and sources:
        for item in sources:
            if not isinstance(item, dict):
                continue
            lines.append(f"- {item.get('name', 'unknown')}: {item.get('count', 0)}")
    else:
        lines.append("- none")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    queue_csv = resolve_path(repo_root, args.queue_csv)
    output_json = resolve_path(repo_root, args.output_json)
    output_md = resolve_path(repo_root, args.output_md)

    rows = load_rows(queue_csv)
    payload = build_dashboard(rows, args.stale_days, args.top_n, queue_csv)

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(output_md, payload, args.top_n)

    print(f"low-confidence dashboard json: {output_json}")
    print(f"low-confidence dashboard md: {output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

