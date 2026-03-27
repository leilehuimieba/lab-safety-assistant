#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import ai_review_kb as ark


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build import-ready KB CSV by merging multiple batches with priority.")
    parser.add_argument("--output-dir", default="artifacts/import_bundle_v1234", help="Output directory.")
    parser.add_argument(
        "--source",
        action="append",
        default=[],
        help="Priority-ordered source item, format: name=path. Higher priority first.",
    )
    return parser.parse_args()


def parse_sources(items: list[str]) -> list[tuple[str, Path]]:
    parsed: list[tuple[str, Path]] = []
    for item in items:
        if "=" not in item:
            raise SystemExit(f"Invalid --source format: {item}. Expected name=path")
        name, raw_path = item.split("=", 1)
        name = name.strip()
        path = Path(raw_path.strip()).resolve()
        if not name:
            raise SystemExit(f"Empty source name in: {item}")
        parsed.append((name, path))
    return parsed


def default_sources() -> list[tuple[str, Path]]:
    repo_root = Path(".").resolve()
    return [
        ("curated", (repo_root / "knowledge_base_curated.csv").resolve()),
        (
            "v4_pass",
            (repo_root / "artifacts" / "v4_repair_round" / "run_20260327_190336" / "second_recheck" / "knowledge_base_recheck_pass.csv").resolve(),
        ),
        ("v3_unified", (repo_root / "artifacts" / "dify_kb_batch_v3" / "knowledge_base_unified.csv").resolve()),
        ("v2_unified", (repo_root / "artifacts" / "dify_kb_batch_v2" / "knowledge_base_unified.csv").resolve()),
        ("v1_unified", (repo_root / "artifacts" / "dify_kb_batch_v1" / "knowledge_base_unified.csv").resolve()),
    ]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def normalize_row(row: dict[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for field in ark.KB_FIELDNAMES:
        normalized[field] = (row.get(field) or "").strip()
    return normalized


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ark.KB_FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in ark.KB_FIELDNAMES})


def count_by(rows: list[dict[str, str]], key: str) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for row in rows:
        counter[(row.get(key) or "").strip() or "unknown"] += 1
    return dict(counter)


def main() -> int:
    args = parse_args()
    source_specs = parse_sources(args.source) if args.source else default_sources()

    missing = [f"{name}={path}" for name, path in source_specs if not path.exists()]
    if missing:
        raise SystemExit("Missing source files:\n" + "\n".join(missing))

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_csv = output_dir / "knowledge_base_import_ready.csv"
    report_json = output_dir / "import_bundle_report.json"
    report_md = output_dir / "import_bundle_report.md"

    merged_rows: list[dict[str, str]] = []
    selected_by_id: dict[str, str] = {}
    source_input_counts: dict[str, int] = {}
    source_selected_counts: Counter[str] = Counter()
    duplicate_skips: Counter[str] = Counter()
    empty_id_count = 0

    for name, path in source_specs:
        rows = read_csv(path)
        source_input_counts[name] = len(rows)
        for raw in rows:
            row = normalize_row(raw)
            row_id = row.get("id", "")
            if not row_id:
                empty_id_count += 1
                continue
            if row_id in selected_by_id:
                duplicate_skips[name] += 1
                continue
            selected_by_id[row_id] = name
            source_selected_counts[name] += 1
            merged_rows.append(row)

    write_csv(output_csv, merged_rows)

    by_category = count_by(merged_rows, "category")
    by_source_type = count_by(merged_rows, "source_type")
    by_language = count_by(merged_rows, "language")
    by_risk = count_by(merged_rows, "risk_level")

    report = {
        "generated_at": now_iso(),
        "output_csv": str(output_csv),
        "total_rows": len(merged_rows),
        "empty_id_skipped": empty_id_count,
        "sources": [
            {"name": name, "path": str(path), "input_rows": source_input_counts.get(name, 0)}
            for name, path in source_specs
        ],
        "selected_rows_by_source": dict(source_selected_counts),
        "duplicate_skips_by_source": dict(duplicate_skips),
        "distribution": {
            "category": by_category,
            "source_type": by_source_type,
            "language": by_language,
            "risk_level": by_risk,
        },
    }
    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines: list[str] = []
    lines.append("# 导入总库构建报告（V1~V4）")
    lines.append("")
    lines.append(f"- 生成时间：`{report['generated_at']}`")
    lines.append(f"- 输出文件：`{output_csv}`")
    lines.append(f"- 合并后总条目：`{len(merged_rows)}`")
    lines.append(f"- 空ID跳过：`{empty_id_count}`")
    lines.append("")
    lines.append("## 来源合并统计（按优先级）")
    lines.append("")
    lines.append("| source | input_rows | selected_rows | duplicate_skips |")
    lines.append("|---|---:|---:|---:|")
    for name, _ in source_specs:
        lines.append(
            f"| {name} | {source_input_counts.get(name, 0)} | {source_selected_counts.get(name, 0)} | {duplicate_skips.get(name, 0)} |"
        )
    lines.append("")
    lines.append("## 分布摘要")
    lines.append("")

    def append_dist(title: str, data: dict[str, int]) -> None:
        lines.append(f"### {title}")
        lines.append("")
        lines.append("| key | count |")
        lines.append("|---|---:|")
        for key, value in sorted(data.items(), key=lambda item: (-item[1], item[0])):
            lines.append(f"| {key} | {value} |")
        lines.append("")

    append_dist("category", by_category)
    append_dist("source_type", by_source_type)
    append_dist("language", by_language)
    append_dist("risk_level", by_risk)

    report_md.write_text("\n".join(lines), encoding="utf-8")

    print("Import-ready bundle built:")
    print(f"- csv: {output_csv}")
    print(f"- report_json: {report_json}")
    print(f"- report_md: {report_md}")
    print(f"- total_rows: {len(merged_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

