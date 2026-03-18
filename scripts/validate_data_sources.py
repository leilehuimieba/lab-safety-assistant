#!/usr/bin/env python3
"""
Validate data_sources CSV schemas and key field constraints.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path


RISK_LEVELS = {"1", "2", "3", "4", "5"}
BOOL_SET = {"true", "false", ""}

MANIFEST_HEADERS = [
    "path",
    "source_title",
    "source_org",
    "category",
    "subcategory",
    "lab_type",
    "risk_level",
    "hazard_types",
    "tags",
    "language",
    "question_hint",
    "reviewer",
]

WEB_HEADERS = [
    "source_id",
    "title",
    "source_org",
    "category",
    "subcategory",
    "lab_type",
    "risk_level",
    "hazard_types",
    "url",
    "tags",
    "language",
    "question_hint",
]

PDF_RULE_HEADERS = [
    "rule_id",
    "path_pattern",
    "force_ocr",
    "body_start_page",
    "skip_pages",
    "notes",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate data_sources CSV files.")
    parser.add_argument("--repo-root", default=".", help="Repository root path.")
    parser.add_argument(
        "--dictionary",
        default="data_sources/field_dictionary.json",
        help="Field dictionary json path (relative to repo root by default).",
    )
    parser.add_argument("--quiet", action="store_true", help="Print concise output.")
    return parser.parse_args()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        rows = list(reader)
    return headers, rows


def load_field_dictionary(path: Path, errors: list[str]) -> dict:
    if not path.exists():
        errors.append(f"缺少字段字典文件：{path}")
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        errors.append(f"字段字典 JSON 解析失败：{path} ({exc})")
        return {}
    if not isinstance(data, dict):
        errors.append(f"字段字典格式非法：{path}（应为 JSON object）")
        return {}
    return data


def validate_manifest(
    path: Path,
    errors: list[str],
    warnings: list[str],
    allowed: dict[str, set[str]],
) -> None:
    if not path.exists():
        errors.append(f"缺少文件：{path}")
        return

    headers, rows = read_csv(path)
    if headers != MANIFEST_HEADERS:
        errors.append(
            f"{path.name} 表头不匹配。\n  expected={MANIFEST_HEADERS}\n  actual={headers}"
        )
        return

    seen_paths: set[str] = set()
    dup_paths: set[str] = set()
    for i, row in enumerate(rows, start=2):
        rel_path = (row.get("path") or "").strip()
        title = (row.get("source_title") or "").strip()
        category = (row.get("category") or "").strip()
        lab_type = (row.get("lab_type") or "").strip()
        risk = (row.get("risk_level") or "").strip()
        language = (row.get("language") or "").strip()
        q_hint = (row.get("question_hint") or "").strip()

        if not rel_path:
            errors.append(f"{path.name} 第{i}行 path 为空")
        if re.match(r"^[A-Za-z]:[\\/]", rel_path) or rel_path.startswith("/"):
            errors.append(f"{path.name} 第{i}行 path 不能是绝对路径：{rel_path}")
        if not title:
            errors.append(f"{path.name} 第{i}行 source_title 为空")
        if category and allowed.get("category") and category not in allowed["category"]:
            errors.append(
                f"{path.name} 第{i}行 category 非法：{category}，允许值见 data_sources/field_dictionary.json"
            )
        if lab_type and allowed.get("lab_type") and lab_type not in allowed["lab_type"]:
            errors.append(
                f"{path.name} 第{i}行 lab_type 非法：{lab_type}，允许值见 data_sources/field_dictionary.json"
            )
        if risk not in RISK_LEVELS:
            errors.append(f"{path.name} 第{i}行 risk_level 非法：{risk}")
        if language and allowed.get("language") and language not in allowed["language"]:
            errors.append(
                f"{path.name} 第{i}行 language 非法：{language}，允许值见 data_sources/field_dictionary.json"
            )
        if not q_hint:
            errors.append(f"{path.name} 第{i}行 question_hint 为空")

        if rel_path:
            if rel_path in seen_paths:
                dup_paths.add(rel_path)
            seen_paths.add(rel_path)

    if dup_paths:
        warnings.append(f"{path.name} 存在重复 path：{sorted(dup_paths)}")


def validate_web_seed(
    path: Path,
    errors: list[str],
    warnings: list[str],
    allowed: dict[str, set[str]],
) -> None:
    if not path.exists():
        errors.append(f"缺少文件：{path}")
        return

    headers, rows = read_csv(path)
    if headers != WEB_HEADERS:
        errors.append(
            f"{path.name} 表头不匹配。\n  expected={WEB_HEADERS}\n  actual={headers}"
        )
        return

    seen_ids: set[str] = set()
    dup_ids: set[str] = set()
    for i, row in enumerate(rows, start=2):
        source_id = (row.get("source_id") or "").strip()
        title = (row.get("title") or "").strip()
        category = (row.get("category") or "").strip()
        lab_type = (row.get("lab_type") or "").strip()
        url = (row.get("url") or "").strip()
        risk = (row.get("risk_level") or "").strip()
        language = (row.get("language") or "").strip()

        if not source_id:
            errors.append(f"{path.name} 第{i}行 source_id 为空")
        if not title:
            errors.append(f"{path.name} 第{i}行 title 为空")
        if category and allowed.get("category") and category not in allowed["category"]:
            errors.append(
                f"{path.name} 第{i}行 category 非法：{category}，允许值见 data_sources/field_dictionary.json"
            )
        if lab_type and allowed.get("lab_type") and lab_type not in allowed["lab_type"]:
            errors.append(
                f"{path.name} 第{i}行 lab_type 非法：{lab_type}，允许值见 data_sources/field_dictionary.json"
            )
        if not url or not re.match(r"^https?://", url):
            errors.append(f"{path.name} 第{i}行 url 非法：{url}")
        if risk not in RISK_LEVELS:
            errors.append(f"{path.name} 第{i}行 risk_level 非法：{risk}")
        if language and allowed.get("language") and language not in allowed["language"]:
            errors.append(
                f"{path.name} 第{i}行 language 非法：{language}，允许值见 data_sources/field_dictionary.json"
            )

        if source_id:
            if source_id in seen_ids:
                dup_ids.add(source_id)
            seen_ids.add(source_id)

    if dup_ids:
        warnings.append(f"{path.name} 存在重复 source_id：{sorted(dup_ids)}")


def validate_pdf_rules(path: Path, errors: list[str], warnings: list[str]) -> None:
    if not path.exists():
        errors.append(f"缺少文件：{path}")
        return

    headers, rows = read_csv(path)
    if headers != PDF_RULE_HEADERS:
        errors.append(
            f"{path.name} 表头不匹配。\n  expected={PDF_RULE_HEADERS}\n  actual={headers}"
        )
        return

    seen_ids: set[str] = set()
    dup_ids: set[str] = set()
    for i, row in enumerate(rows, start=2):
        rule_id = (row.get("rule_id") or "").strip()
        pattern = (row.get("path_pattern") or "").strip()
        force_ocr = (row.get("force_ocr") or "").strip().lower()
        start_page = (row.get("body_start_page") or "").strip()

        if not rule_id:
            errors.append(f"{path.name} 第{i}行 rule_id 为空")
        if not pattern:
            errors.append(f"{path.name} 第{i}行 path_pattern 为空")
        if force_ocr not in BOOL_SET:
            errors.append(f"{path.name} 第{i}行 force_ocr 非法：{force_ocr}")
        if start_page and (not start_page.isdigit() or int(start_page) <= 0):
            errors.append(f"{path.name} 第{i}行 body_start_page 非法：{start_page}")

        if rule_id:
            if rule_id in seen_ids:
                dup_ids.add(rule_id)
            seen_ids.add(rule_id)

    if dup_ids:
        warnings.append(f"{path.name} 存在重复 rule_id：{sorted(dup_ids)}")


def print_summary(errors: list[str], warnings: list[str], quiet: bool) -> None:
    if not errors and not warnings:
        print("data_sources schema check passed.")
        return

    if errors:
        print("data_sources schema check failed:")
        for item in errors:
            print(f"- {item}")
    else:
        print("data_sources schema check passed with warnings:")

    if warnings and not quiet:
        for item in warnings:
            print(f"- {item}")


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    base = repo_root / "data_sources"
    dictionary_path = Path(args.dictionary)
    if not dictionary_path.is_absolute():
        dictionary_path = repo_root / dictionary_path

    errors: list[str] = []
    warnings: list[str] = []
    field_dict = load_field_dictionary(dictionary_path, errors)

    manifest_allowed = {
        "category": set(field_dict.get("document_manifest", {}).get("category", [])),
        "lab_type": set(field_dict.get("document_manifest", {}).get("lab_type", [])),
        "language": set(field_dict.get("document_manifest", {}).get("language", [])),
    }
    web_allowed = {
        "category": set(field_dict.get("web_seed_urls", {}).get("category", [])),
        "lab_type": set(field_dict.get("web_seed_urls", {}).get("lab_type", [])),
        "language": set(field_dict.get("web_seed_urls", {}).get("language", [])),
    }

    validate_manifest(base / "document_manifest.csv", errors, warnings, manifest_allowed)
    validate_web_seed(base / "web_seed_urls.csv", errors, warnings, web_allowed)
    validate_pdf_rules(base / "pdf_special_rules.csv", errors, warnings)

    print_summary(errors, warnings, args.quiet)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
