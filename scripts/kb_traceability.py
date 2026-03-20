#!/usr/bin/env python3
"""
Knowledge Base Traceability Enhancement Script

This script helps improve the traceability fields in the knowledge base.
It can:
1. Generate a report of entries with missing traceability info
2. Batch update traceability fields based on patterns
3. Validate traceability completeness
"""

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class TraceabilityReport:
    total: int
    complete: int
    incomplete: int
    missing_fields: dict[str, list[str]]


TRACEABILITY_FIELDS = [
    "source_type",
    "source_title",
    "source_org",
    "source_version",
    "source_date",
    "source_url",
]

FIELD_LABELS = {
    "source_type": "来源类型",
    "source_title": "来源标题",
    "source_org": "来源机构",
    "source_version": "版本号",
    "source_date": "发布日期",
    "source_url": "来源URL",
}

PLACEHOLDER_VALUES = ["待补充", "", "无", "暂无"]


def is_missing(value: str) -> bool:
    return not value or value.strip() in PLACEHOLDER_VALUES


def analyze_traceability(kb_path: Path) -> TraceabilityReport:
    with kb_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    report = TraceabilityReport(total=len(rows), complete=0, incomplete=0, missing_fields={})

    for field in TRACEABILITY_FIELDS:
        report.missing_fields[field] = []

    for idx, row in enumerate(rows, start=2):
        entry_id = row.get("id", f"row_{idx}")
        is_entry_complete = True

        for field in TRACEABILITY_FIELDS:
            value = row.get(field, "")
            if is_missing(value):
                report.missing_fields[field].append(entry_id)
                is_entry_complete = False

        if is_entry_complete:
            report.complete += 1
        else:
            report.incomplete += 1

    return report


def print_report(report: TraceabilityReport) -> None:
    print("=" * 60)
    print("知识库溯源完整性报告")
    print("=" * 60)
    print(f"总条目数: {report.total}")
    print(f"完整溯源: {report.complete} ({100*report.complete/report.total:.1f}%)")
    print(f"缺失溯源: {report.incomplete} ({100*report.incomplete/report.total:.1f}%)")
    print()
    print("各字段缺失情况:")
    print("-" * 40)
    for field, entries in report.missing_fields.items():
        label = FIELD_LABELS.get(field, field)
        pct = 100 * len(entries) / report.total if report.total > 0 else 0
        print(f"  {field}: {len(entries)}/{report.total} ({pct:.1f}%) - {label}")
    print()


def generate_template_csv(kb_path: Path, output_path: Path) -> None:
    with kb_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    incomplete_ids = set()
    for idx, row in enumerate(rows, start=2):
        for field in TRACEABILITY_FIELDS:
            if is_missing(row.get(field, "")):
                incomplete_ids.add(row.get("id", f"row_{idx}"))

    output_fieldnames = list(fieldnames) + ["traceability_status"]
    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=output_fieldnames)
        writer.writeheader()
        for row in rows:
            entry_id = row.get("id", "")
            if entry_id in incomplete_ids:
                row["traceability_status"] = "needs_review"
            else:
                row["traceability_status"] = "complete"
            writer.writerow(row)

    print(f"已生成模板文件: {output_path}")
    print(f"需完善的条目数: {len(incomplete_ids)}")


def infer_traceability_from_title(title: str, category: str) -> dict:
    inferred = {}

    chemical_names = ["乙醇", "甲醇", "丙酮", "乙醚", "盐酸", "硫酸", "硝酸", "氢氧化钠", "过氧化氢", "氯仿"]
    for chem in chemical_names:
        if chem in title:
            inferred["source_type"] = "MSDS"
            inferred["source_title"] = f"MSDS-{chem}"
            inferred["source_org"] = "化学品供应商"
            inferred["source_date"] = datetime.now().strftime("%Y-%m-%d")
            break

    if "SOP" in title or "操作" in title:
        inferred["source_type"] = "SOP"
        inferred["source_title"] = title[:50]
        inferred["source_org"] = "实验室管理处"
        inferred["source_date"] = datetime.now().strftime("%Y-%m-%d")

    if "应急" in title or "处置" in category:
        inferred["source_type"] = "应急预案"
        inferred["source_title"] = title[:50]
        inferred["source_org"] = "实验室管理处"
        inferred["source_date"] = datetime.now().strftime("%Y-%m-%d")

    if "制度" in title or "管理" in category:
        inferred["source_type"] = "制度"
        inferred["source_title"] = title[:50]
        inferred["source_org"] = "实验室管理处"
        inferred["source_date"] = datetime.now().strftime("%Y-%m-%d")

    return inferred


def batch_update_traceability(kb_path: Path, dry_run: bool = True) -> int:
    with kb_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    updated_count = 0
    for row in rows:
        needs_update = False
        for field in TRACEABILITY_FIELDS:
            if is_missing(row.get(field, "")):
                inferred = infer_traceability_from_title(row.get("title", ""), row.get("category", ""))
                if field in inferred:
                    row[field] = inferred[field]
                    needs_update = True
                    updated_count += 1

        if needs_update and not dry_run:
            if row.get("status") == "draft":
                row["status"] = "pending_review"

    if not dry_run:
        with kb_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"已更新 {updated_count} 个字段")
    else:
        print(f"[Dry Run] 将会更新 {updated_count} 个字段")
        print("使用 --apply 参数实际执行更新")

    return updated_count


def validate_traceability(kb_path: Path) -> tuple[bool, list[str]]:
    with kb_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    errors = []

    required_fields = ["source_type", "source_title", "source_org", "source_date"]
    for idx, row in enumerate(rows, start=2):
        entry_id = row.get("id", f"row_{idx}")
        for field in required_fields:
            if is_missing(row.get(field, "")):
                errors.append(f"{entry_id}: 必填字段 {field} 为空")

    valid_source_types = {"SOP", "MSDS", "制度", "应急预案", "网页", "经验", "法规", "标准"}
    for idx, row in enumerate(rows, start=2):
        source_type = row.get("source_type", "")
        entry_id = row.get("id", f"row_{idx}")
        if source_type and source_type not in valid_source_types:
            errors.append(f"{entry_id}: source_type '{source_type}' 不在允许列表中")

    return len(errors) == 0, errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="知识库溯源字段完善工具"
    )
    parser.add_argument(
        "--kb-path",
        type=Path,
        default=Path("knowledge_base_curated.csv"),
        help="知识库文件路径",
    )
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    report_parser = subparsers.add_parser("report", help="生成溯源完整性报告")
    report_parser.add_argument("--verbose", action="store_true", help="显示详细信息")

    template_parser = subparsers.add_parser("template", help="生成待完善条目模板")
    template_parser.add_argument(
        "--output",
        type=Path,
        default=Path("knowledge_base_traceability_template.csv"),
        help="输出文件路径",
    )

    update_parser = subparsers.add_parser("update", help="批量更新溯源字段")
    update_parser.add_argument(
        "--apply", action="store_true", help="实际执行更新（默认仅 dry run）"
    )

    validate_parser = subparsers.add_parser("validate", help="验证溯源完整性")

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.command == "report":
        report = analyze_traceability(args.kb_path)
        print_report(report)
        if args.verbose:
            for field, entries in report.missing_fields.items():
                if entries:
                    print(f"\n{field} 缺失的条目 ({len(entries)}):")
                    for eid in entries[:10]:
                        print(f"  - {eid}")
                    if len(entries) > 10:
                        print(f"  ... 还有 {len(entries) - 10} 个")

    elif args.command == "template":
        generate_template_csv(args.kb_path, args.output)

    elif args.command == "update":
        batch_update_traceability(args.kb_path, dry_run=not args.apply)

    elif args.command == "validate":
        is_valid, errors = validate_traceability(args.kb_path)
        if is_valid:
            print("溯源验证通过")
            return 0
        else:
            print("溯源验证失败:")
            for err in errors:
                print(f"  - {err}")
            return 1

    else:
        report = analyze_traceability(args.kb_path)
        print_report(report)
        print("使用 --help 查看可用子命令")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
