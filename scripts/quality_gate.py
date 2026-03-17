#!/usr/bin/env python3
"""
Repository quality gate for lightweight CI and local checks.

Checks include:
- Secret scan (high-confidence patterns)
- Knowledge base schema and ID integrity
- Eval set schema and value integrity
- Rule ID integrity for safety_rules.yaml
"""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
from pathlib import Path


KB_FIELDNAMES = [
    "id",
    "title",
    "category",
    "subcategory",
    "lab_type",
    "risk_level",
    "hazard_types",
    "scenario",
    "question",
    "answer",
    "steps",
    "ppe",
    "forbidden",
    "disposal",
    "first_aid",
    "emergency",
    "legal_notes",
    "references",
    "source_type",
    "source_title",
    "source_org",
    "source_version",
    "source_date",
    "source_url",
    "last_updated",
    "reviewer",
    "status",
    "tags",
    "language",
]

EVAL_FIELDNAMES = [
    "id",
    "domain",
    "scenario",
    "risk_level",
    "question",
    "expected_keypoints",
    "expected_action",
    "allowed_sources",
    "should_refuse",
    "evaluation_type",
    "notes",
]

ALLOWED_SHOULD_REFUSE = {"yes", "no"}
ALLOWED_EVAL_TYPES = {"qa", "safety", "emergency"}
RISK_LEVELS = {"1", "2", "3", "4", "5"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run repository quality checks.")
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root directory. Default: current directory.",
    )
    parser.add_argument(
        "--skip-secret-scan",
        action="store_true",
        help="Skip secret scan step.",
    )
    return parser.parse_args()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
        rows = list(reader)
    return headers, rows


def check_kb(repo_root: Path, errors: list[str]) -> None:
    path = repo_root / "knowledge_base_curated.csv"
    if not path.exists():
        errors.append("缺少 knowledge_base_curated.csv")
        return

    headers, rows = read_csv(path)
    if headers != KB_FIELDNAMES:
        errors.append(
            "knowledge_base_curated.csv 表头不匹配预期 schema。"
            f"\n  expected={KB_FIELDNAMES}\n  actual={headers}"
        )

    if len(rows) < 50:
        errors.append(f"knowledge_base_curated.csv 条目数过少：{len(rows)}（期望 >= 50）")

    id_seen: set[str] = set()
    duplicates: list[str] = []
    for index, row in enumerate(rows, start=2):
        row_id = (row.get("id") or "").strip()
        if not row_id:
            errors.append(f"knowledge_base_curated.csv 第 {index} 行 id 为空")
            continue
        if row_id in id_seen:
            duplicates.append(row_id)
        id_seen.add(row_id)

        for required in ("title", "question", "answer", "category"):
            if not (row.get(required) or "").strip():
                errors.append(f"knowledge_base_curated.csv 第 {index} 行 {required} 为空")

        risk = (row.get("risk_level") or "").strip()
        if risk and risk not in RISK_LEVELS:
            errors.append(f"knowledge_base_curated.csv 第 {index} 行 risk_level 非法：{risk}")

    if duplicates:
        errors.append(f"knowledge_base_curated.csv 存在重复 id：{sorted(set(duplicates))}")


def check_eval(repo_root: Path, errors: list[str]) -> None:
    path = repo_root / "eval_set_v1.csv"
    if not path.exists():
        errors.append("缺少 eval_set_v1.csv")
        return

    headers, rows = read_csv(path)
    if headers != EVAL_FIELDNAMES:
        errors.append(
            "eval_set_v1.csv 表头不匹配预期 schema。"
            f"\n  expected={EVAL_FIELDNAMES}\n  actual={headers}"
        )

    if len(rows) < 30:
        errors.append(f"eval_set_v1.csv 条目数过少：{len(rows)}（期望 >= 30）")

    id_seen: set[str] = set()
    duplicates: list[str] = []
    for index, row in enumerate(rows, start=2):
        row_id = (row.get("id") or "").strip()
        if not row_id:
            errors.append(f"eval_set_v1.csv 第 {index} 行 id 为空")
            continue
        if row_id in id_seen:
            duplicates.append(row_id)
        id_seen.add(row_id)

        if not (row.get("question") or "").strip():
            errors.append(f"eval_set_v1.csv 第 {index} 行 question 为空")

        should_refuse = (row.get("should_refuse") or "").strip().lower()
        if should_refuse not in ALLOWED_SHOULD_REFUSE:
            errors.append(
                f"eval_set_v1.csv 第 {index} 行 should_refuse 非法：{should_refuse}"
            )

        eval_type = (row.get("evaluation_type") or "").strip().lower()
        if eval_type not in ALLOWED_EVAL_TYPES:
            errors.append(
                f"eval_set_v1.csv 第 {index} 行 evaluation_type 非法：{eval_type}"
            )

        risk = (row.get("risk_level") or "").strip()
        if risk and risk not in RISK_LEVELS:
            errors.append(f"eval_set_v1.csv 第 {index} 行 risk_level 非法：{risk}")

    if duplicates:
        errors.append(f"eval_set_v1.csv 存在重复 id：{sorted(set(duplicates))}")


def check_rules(repo_root: Path, errors: list[str]) -> None:
    path = repo_root / "safety_rules.yaml"
    if not path.exists():
        errors.append("缺少 safety_rules.yaml")
        return

    content = path.read_text(encoding="utf-8")
    ids = re.findall(r"^\s*-\s*id:\s*(R-\d{3})\s*$", content, flags=re.MULTILINE)
    if len(ids) < 10:
        errors.append(f"safety_rules.yaml 规则数量过少：{len(ids)}（期望 >= 10）")
    if len(ids) != len(set(ids)):
        duplicates = sorted({item for item in ids if ids.count(item) > 1})
        errors.append(f"safety_rules.yaml 存在重复规则 ID：{duplicates}")


def run_secret_scan(repo_root: Path, errors: list[str]) -> None:
    cmd = [
        sys.executable,
        str(repo_root / "scripts" / "secret_scan.py"),
        "--repo-root",
        str(repo_root),
        "--quiet",
    ]
    completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        errors.append(
            "secret_scan 检查未通过。"
            + (f"\n  detail: {completed.stdout.strip()}" if completed.stdout else "")
        )


def print_summary(errors: list[str]) -> None:
    if not errors:
        print("Quality gate passed.")
        return
    print("Quality gate failed with issues:")
    for item in errors:
        print(f"- {item}")


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    errors: list[str] = []

    if not args.skip_secret_scan:
        run_secret_scan(repo_root, errors)
    check_kb(repo_root, errors)
    check_eval(repo_root, errors)
    check_rules(repo_root, errors)

    print_summary(errors)
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

