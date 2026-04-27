#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate prefetch markdown report and assignment CSV from prefetch status."
    )
    parser.add_argument("--status-csv", required=True, help="Input prefetch status CSV path.")
    parser.add_argument("--output-report", required=True, help="Output markdown report path.")
    parser.add_argument(
        "--output-assignment",
        default="",
        help="Output assignment CSV path. If empty, assignment file is not generated.",
    )
    parser.add_argument(
        "--low-quality-threshold",
        type=float,
        default=0.70,
        help="Quality score threshold for low quality rows.",
    )
    parser.add_argument(
        "--batch-name",
        default="web_seed_batch",
        help="Display name used in report title.",
    )
    return parser.parse_args()


def parse_quality(raw: str) -> float:
    try:
        return float(raw)
    except Exception:
        return 0.0


def is_non_ok(status: str) -> bool:
    status = (status or "").strip().lower()
    return status not in {"ok", ""}


def status_bucket(status: str) -> str:
    status = (status or "").strip().lower()
    if status == "ok":
        return "ok"
    if status == "blocked":
        return "blocked"
    if status in {"error", "timeout", "not_found"}:
        return "failed"
    return "non_ok"


def pct(part: int, total: int) -> str:
    if total <= 0:
        return "0.0%"
    return f"{(part * 100.0 / total):.1f}%"


def suggested_action(row: dict[str, str], low_quality_threshold: float) -> tuple[str, str, str]:
    source_id = (row.get("source_id") or "").strip()
    title = (row.get("title") or "").strip()
    status = (row.get("status") or "").strip().lower()
    score = parse_quality(row.get("quality_score") or "")

    if status in {"blocked", "error", "timeout", "not_found"}:
        return (
            "collector",
            "replace_link_or_manual_upload",
            f"Replace inaccessible source for {source_id} ({title}) with official mirror or upload original file to manual_sources.",
        )
    if score < low_quality_threshold:
        return (
            "cleaner",
            "rewrite_structured_summary",
            f"Manually clean and rewrite {source_id} ({title}) into answer/steps/ppe/forbidden/emergency structure.",
        )
    return ("", "", "")


def main() -> int:
    args = parse_args()
    status_csv = Path(args.status_csv).resolve()
    output_report = Path(args.output_report).resolve()
    output_assignment = Path(args.output_assignment).resolve() if args.output_assignment else None

    if not status_csv.exists():
        raise SystemExit(f"Status CSV not found: {status_csv}")

    with status_csv.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    total = len(rows)
    ok_rows = [r for r in rows if (r.get("status") or "").strip().lower() == "ok"]
    blocked_rows = [r for r in rows if status_bucket(r.get("status") or "") == "blocked"]
    failed_rows = [r for r in rows if status_bucket(r.get("status") or "") == "failed"]
    low_quality_rows = [
        r
        for r in rows
        if parse_quality(r.get("quality_score") or "") < args.low_quality_threshold
    ]

    report_lines: list[str] = []
    report_lines.append(f"# {args.batch_name} Prefetch Report")
    report_lines.append("")
    report_lines.append(f"- Total sources: `{total}`")
    report_lines.append(f"- Fetchable (`status=ok`): `{len(ok_rows)}` ({pct(len(ok_rows), total)})")
    report_lines.append(f"- Blocked (`status=blocked`): `{len(blocked_rows)}` ({pct(len(blocked_rows), total)})")
    report_lines.append(
        f"- Failed (`status=error/timeout/not_found`): `{len(failed_rows)}` ({pct(len(failed_rows), total)})"
    )
    report_lines.append(
        f"- Low quality (`quality_score < {args.low_quality_threshold:.2f}`): `{len(low_quality_rows)}` ({pct(len(low_quality_rows), total)})"
    )
    report_lines.append("")

    report_lines.append("## Blocked / Failed Items (Collector First)")
    report_lines.append("")
    report_lines.append("| source_id | status | title | suggested_action |")
    report_lines.append("|---|---|---|---|")
    for r in rows:
        status = (r.get("status") or "").strip().lower()
        if status in {"blocked", "error", "timeout", "not_found"}:
            report_lines.append(
                f"| {(r.get('source_id') or '').strip()} | {status} | {(r.get('title') or '').strip()} | collector: replace with official mirror or provide downloadable attachment |"
            )
    report_lines.append("")

    report_lines.append("## Low Quality Items (Cleaner First)")
    report_lines.append("")
    report_lines.append("| source_id | status | quality_score | title | suggested_action |")
    report_lines.append("|---|---|---:|---|---|")
    for r in low_quality_rows:
        report_lines.append(
            f"| {(r.get('source_id') or '').strip()} | {(r.get('status') or '').strip()} | {parse_quality(r.get('quality_score') or ''):.4f} | {(r.get('title') or '').strip()} | cleaner: manually review and rewrite structured summary |"
        )
    report_lines.append("")

    report_lines.append("## Import Plan")
    report_lines.append("")
    report_lines.append("1. Import `ok` rows from prefetch knowledge_base_web.csv into staging KB.")
    report_lines.append("2. Resolve blocked/error rows by collector and rerun one prefetch round.")
    report_lines.append("3. Clean low-quality rows before moving to official release batch.")
    report_lines.append("")

    output_report.parent.mkdir(parents=True, exist_ok=True)
    output_report.write_text("\n".join(report_lines), encoding="utf-8")

    if output_assignment:
        tasks: list[dict[str, str]] = []
        for r in rows:
            assignee, task_type, action = suggested_action(r, args.low_quality_threshold)
            if not assignee:
                continue
            status = (r.get("status") or "").strip().lower()
            priority = "P1" if status in {"blocked", "error", "timeout", "not_found"} else "P2"
            tasks.append(
                {
                    "source_id": (r.get("source_id") or "").strip(),
                    "title": (r.get("title") or "").strip(),
                    "url": (r.get("url") or "").strip(),
                    "status": (r.get("status") or "").strip(),
                    "quality_score": f"{parse_quality(r.get('quality_score') or ''):.4f}",
                    "assignee_role": assignee,
                    "task_type": task_type,
                    "priority": priority,
                    "suggested_action": action,
                }
            )
        output_assignment.parent.mkdir(parents=True, exist_ok=True)
        with output_assignment.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "source_id",
                    "title",
                    "url",
                    "status",
                    "quality_score",
                    "assignee_role",
                    "task_type",
                    "priority",
                    "suggested_action",
                ],
            )
            writer.writeheader()
            for row in tasks:
                writer.writerow(row)

    print(f"Prefetch report generated: {output_report}")
    if output_assignment:
        print(f"Task assignment generated: {output_assignment}")
    print(f"- total: {total}")
    print(f"- ok: {len(ok_rows)}")
    print(f"- blocked: {len(blocked_rows)}")
    print(f"- failed: {len(failed_rows)}")
    print(f"- low_quality: {len(low_quality_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
