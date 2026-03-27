#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class ManifestJob:
    name: str
    input_csv: Path
    output_csv: Path


DEFAULT_JOBS = [
    ManifestJob("v1", Path("data_sources/web_seed_urls.csv"), Path("data_sources/web_seed_urls_v1_1_candidates.csv")),
    ManifestJob(
        "v2",
        Path("data_sources/web_seed_urls_v2_candidates.csv"),
        Path("data_sources/web_seed_urls_v2_1_candidates.csv"),
    ),
    ManifestJob(
        "v3",
        Path("data_sources/web_seed_urls_v3_candidates.csv"),
        Path("data_sources/web_seed_urls_v3_1_candidates.csv"),
    ),
]


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply official relink map to web seed manifests.")
    parser.add_argument(
        "--map-csv",
        default="data_sources/relink_official_map_v4_1.csv",
        help="Relink map CSV path.",
    )
    parser.add_argument(
        "--report-dir",
        default="artifacts/relink_v4_1",
        help="Directory for relink report outputs.",
    )
    return parser.parse_args()


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        return (reader.fieldnames or []), rows


def write_rows(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def parse_map(path: Path) -> dict[str, dict[str, str]]:
    _, rows = read_rows(path)
    output: dict[str, dict[str, str]] = {}
    for row in rows:
        sid = (row.get("source_id") or "").strip()
        if sid:
            output[sid] = row
    return output


def append_tag(raw: str, token: str) -> str:
    parts = [item.strip() for item in (raw or "").split(";") if item.strip()]
    if token not in parts:
        parts.append(token)
    return ";".join(parts)


def apply_job(job: ManifestJob, mapping: dict[str, dict[str, str]]) -> tuple[int, int, list[dict[str, str]]]:
    fieldnames, rows = read_rows(job.input_csv)
    missing = 0
    changed = 0
    detail_rows: list[dict[str, str]] = []

    for row in rows:
        sid = (row.get("source_id") or "").strip()
        if not sid:
            continue
        relink = mapping.get(sid)
        if not relink:
            continue

        old_url = (row.get("url") or "").strip()
        expected_old = (relink.get("old_url") or "").strip()
        new_url = (relink.get("new_url") or "").strip()
        if not new_url:
            missing += 1
            continue

        row["url"] = new_url

        new_org = (relink.get("new_source_org") or "").strip()
        new_title = (relink.get("new_title") or "").strip()
        if new_org:
            row["source_org"] = new_org
        if new_title:
            row["title"] = new_title

        if "tags" in row:
            row["tags"] = append_tag(row.get("tags", ""), "official_relink_v4_1")
        if "suggested_tags" in row:
            row["suggested_tags"] = append_tag(row.get("suggested_tags", ""), "official_relink_v4_1")

        changed += 1
        detail_rows.append(
            {
                "manifest": job.name,
                "source_id": sid,
                "old_url_actual": old_url,
                "old_url_expected": expected_old,
                "new_url": new_url,
                "new_source_org": new_org,
                "new_title": new_title,
                "replacement_reason": (relink.get("replacement_reason") or "").strip(),
                "confidence": (relink.get("confidence") or "").strip(),
                "old_url_match": "yes" if not expected_old or old_url == expected_old else "no",
            }
        )

    write_rows(job.output_csv, fieldnames, rows)
    return changed, missing, detail_rows


def main() -> int:
    args = parse_args()
    map_csv = Path(args.map_csv).resolve()
    report_dir = Path(args.report_dir).resolve()
    report_dir.mkdir(parents=True, exist_ok=True)

    if not map_csv.exists():
        raise SystemExit(f"Map CSV not found: {map_csv}")

    mapping = parse_map(map_csv)
    if not mapping:
        raise SystemExit(f"No source_id entries found in map CSV: {map_csv}")

    detail_rows: list[dict[str, str]] = []
    summary_rows: list[dict[str, str]] = []

    for job in DEFAULT_JOBS:
        if not job.input_csv.exists():
            raise SystemExit(f"Manifest not found: {job.input_csv}")
        changed, missing, rows = apply_job(job, mapping)
        detail_rows.extend(rows)
        summary_rows.append(
            {
                "manifest": job.name,
                "input_csv": str(job.input_csv),
                "output_csv": str(job.output_csv),
                "changed_rows": str(changed),
                "missing_replacement_url": str(missing),
            }
        )

    detail_csv = report_dir / "official_relink_details.csv"
    summary_csv = report_dir / "official_relink_summary.csv"
    summary_md = report_dir / "official_relink_summary.md"

    if detail_rows:
        write_rows(
            detail_csv,
            [
                "manifest",
                "source_id",
                "old_url_actual",
                "old_url_expected",
                "new_url",
                "new_source_org",
                "new_title",
                "replacement_reason",
                "confidence",
                "old_url_match",
            ],
            detail_rows,
        )
    else:
        write_rows(
            detail_csv,
            [
                "manifest",
                "source_id",
                "old_url_actual",
                "old_url_expected",
                "new_url",
                "new_source_org",
                "new_title",
                "replacement_reason",
                "confidence",
                "old_url_match",
            ],
            [],
        )

    write_rows(summary_csv, ["manifest", "input_csv", "output_csv", "changed_rows", "missing_replacement_url"], summary_rows)

    lines: list[str] = []
    lines.append("# Official Relink Summary (V4.1)")
    lines.append("")
    lines.append(f"- generated_at: `{now_iso()}`")
    lines.append(f"- mapping_file: `{map_csv}`")
    lines.append(f"- detail_csv: `{detail_csv}`")
    lines.append("")
    lines.append("| manifest | input_csv | output_csv | changed_rows | missing_replacement_url |")
    lines.append("|---|---|---|---:|---:|")
    for row in summary_rows:
        lines.append(
            f"| {row['manifest']} | {row['input_csv']} | {row['output_csv']} | {row['changed_rows']} | {row['missing_replacement_url']} |"
        )
    lines.append("")
    lines.append("## Relinked IDs")
    lines.append("")
    for row in detail_rows:
        lines.append(
            f"- `{row['source_id']}`: `{row['old_url_actual']}` -> `{row['new_url']}` (match={row['old_url_match']}, confidence={row['confidence']})"
        )

    summary_md.write_text("\n".join(lines), encoding="utf-8")

    print("Relink manifests generated:")
    for row in summary_rows:
        print(f"- {row['manifest']}: {row['output_csv']} (changed={row['changed_rows']})")
    print(f"- detail: {detail_csv}")
    print(f"- summary: {summary_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

