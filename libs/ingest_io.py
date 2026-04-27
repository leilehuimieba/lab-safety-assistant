from __future__ import annotations

"""Pipeline 共享 IO 与文本处理工具

为 scripts/pipeline/ 下的数据流水线提供通用能力：
- KB_FIELDNAMES: 知识库 CSV 标准字段名
- clean_document_text / clean_line: 文档/网页文本清洗与去噪
- split_into_chunks: 按最大字符数与重叠度切分文本片段
- write_jsonl / write_csv / merge_into_csv: 标准格式写入与增量合并
- sha1_text / normalize_rel_path: 哈希与路径规范化
"""

import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Iterable

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
NOISE_PATTERNS = [
    r"^\d+$",
    r"^第?\s*\d+\s*页$",
    r"^Page\s+\d+$",
    r"^版权所有",
    r"^Copyright",
    r"^目录$",
    r"^Contents$",
]

def clean_line(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def clean_document_text(text: str) -> str:
    text = text.replace("\r", "\n")
    text = text.replace("\x00", "")
    raw_lines = [clean_line(line) for line in text.splitlines()]
    lines: list[str] = []
    previous = ""
    for line in raw_lines:
        if not line:
            continue
        if any(re.search(pattern, line, re.IGNORECASE) for pattern in NOISE_PATTERNS):
            continue
        if line == previous:
            continue
        previous = line
        lines.append(line)
    return "\n".join(lines).strip()
def split_into_chunks(text: str, max_chars: int, overlap: int) -> list[str]:
    paragraphs = [part.strip() for part in text.split("\n") if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if not current:
            current = paragraph
            continue
        candidate = f"{current}\n{paragraph}"
        if len(candidate) <= max_chars:
            current = candidate
            continue
        chunks.append(current)
        if overlap > 0 and len(current) > overlap:
            current = current[-overlap:] + "\n" + paragraph
        else:
            current = paragraph
    if current:
        chunks.append(current)
    return [chunk.strip() for chunk in chunks if chunk.strip()]

def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=KB_FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

def merge_into_csv(path: Path, new_rows: list[dict]) -> int:
    existing_rows: list[dict] = []
    existing_ids: set[str] = set()
    if path.exists():
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                normalized = {field: row.get(field, "") for field in KB_FIELDNAMES}
                existing_rows.append(normalized)
                existing_ids.add(normalized["id"])

    appended = 0
    for row in new_rows:
        if row["id"] in existing_ids:
            continue
        existing_rows.append({field: row.get(field, "") for field in KB_FIELDNAMES})
        existing_ids.add(row["id"])
        appended += 1

    write_csv(path, existing_rows)
    return appended
def sha1_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()

def normalize_rel_path(value: str) -> str:
    return value.replace("/", "\\").strip().lower()
