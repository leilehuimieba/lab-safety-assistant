#!/usr/bin/env python3
"""
Validate docs/release_review_log.md entry completeness and value constraints.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


REQUIRED_KEYS = [
    "审核日期",
    "审核人A",
    "审核人B",
    "使用评测集版本",
    "人工审核题数",
    "通过题数",
    "高风险错误建议（0/1+）",
    "结论（允许发布 yes/no）",
    "备注",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate release review markdown log.")
    parser.add_argument("--repo-root", default=".", help="Repository root.")
    parser.add_argument(
        "--file",
        default="docs/release_review_log.md",
        help="Release review markdown path (relative to repo root).",
    )
    parser.add_argument(
        "--require-entry",
        action="store_true",
        help="Fail if no release entry block is found.",
    )
    parser.add_argument("--quiet", action="store_true", help="Concise output.")
    return parser.parse_args()


def extract_entries(lines: list[str]) -> list[tuple[str, dict[str, str]]]:
    filtered: list[str] = []
    in_code = False
    for ln in lines:
        if ln.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        filtered.append(ln)

    entries: list[tuple[str, dict[str, str]]] = []
    indices = [i for i, ln in enumerate(filtered) if ln.startswith("## 发布批次：")]
    for idx, start in enumerate(indices):
        end = indices[idx + 1] if idx + 1 < len(indices) else len(filtered)
        block = filtered[start:end]
        title = block[0].replace("## 发布批次：", "").strip()
        data: dict[str, str] = {}

        for ln in block[1:]:
            m = re.match(r"^\s*-\s*([^：]+(?:（[^）]+）)?)：\s*(.*)\s*$", ln)
            if not m:
                continue
            k = m.group(1).strip()
            v = m.group(2).strip()
            data[k] = v
        entries.append((title, data))
    return entries


def validate_entry(title: str, data: dict[str, str], errors: list[str]) -> None:
    for key in REQUIRED_KEYS:
        if not (data.get(key) or "").strip():
            errors.append(f"[{title}] 缺少或为空字段：{key}")

    q_raw = (data.get("人工审核题数") or "").strip()
    p_raw = (data.get("通过题数") or "").strip()
    e_raw = (data.get("高风险错误建议（0/1+）") or "").strip()
    allow_raw = (data.get("结论（允许发布 yes/no）") or "").strip().lower()

    if q_raw and (not q_raw.isdigit() or int(q_raw) <= 0):
        errors.append(f"[{title}] 人工审核题数非法：{q_raw}")
    if p_raw and (not p_raw.isdigit() or int(p_raw) < 0):
        errors.append(f"[{title}] 通过题数非法：{p_raw}")
    if e_raw and (not e_raw.isdigit() or int(e_raw) < 0):
        errors.append(f"[{title}] 高风险错误建议计数非法：{e_raw}")

    if q_raw.isdigit() and p_raw.isdigit() and int(p_raw) > int(q_raw):
        errors.append(f"[{title}] 通过题数不能大于人工审核题数：{p_raw}>{q_raw}")

    if allow_raw not in {"yes", "no"}:
        errors.append(f"[{title}] 结论必须是 yes/no：{allow_raw}")

    if e_raw.isdigit() and allow_raw == "yes" and int(e_raw) > 0:
        errors.append(f"[{title}] 高风险错误建议>0 时不允许发布（yes）")


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    path = repo_root / args.file

    if not path.exists():
        print(f"missing file: {path}")
        return 1

    lines = path.read_text(encoding="utf-8").splitlines()
    entries = extract_entries(lines)

    if not entries:
        if args.require_entry:
            print("release_review_log check failed: no release entries found.")
            return 1
        if not args.quiet:
            print("release_review_log check passed: no entries yet (template mode).")
        return 0

    errors: list[str] = []
    for title, data in entries:
        validate_entry(title, data, errors)

    if errors:
        print("release_review_log check failed:")
        for item in errors:
            print(f"- {item}")
        return 1

    if not args.quiet:
        print(f"release_review_log check passed ({len(entries)} entries).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
