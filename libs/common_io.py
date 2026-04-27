"""通用 I/O 工具：CSV、JSON、YAML 读写 + 时间格式化"""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    """返回当前本地时区的 ISO 8601 时间字符串（精确到秒）。"""
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_json(path: Path | str) -> dict[str, Any]:
    """读取 JSON 文件为 dict。"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_json_list(path: Path | str) -> list[dict[str, Any]]:
    """读取 JSON 文件为 list[dict]；文件不存在或格式不符时返回 []。"""
    p = Path(path)
    if not p.exists():
        return []
    with p.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def save_json(path: Path | str, data: Any, indent: int = 2) -> None:
    """将数据写入 JSON 文件，自动创建父目录。"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)


def read_csv_rows(path: Path | str) -> tuple[list[str], list[dict[str, str]]]:
    """读取 CSV 文件，返回 (fieldnames, rows)。"""
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    return fieldnames, rows


def read_csv(path: Path | str) -> list[dict[str, str]]:
    """读取 CSV 文件，仅返回 rows。"""
    _, rows = read_csv_rows(path)
    return rows


def write_csv(
    path: Path | str,
    rows: list[dict[str, str]],
    fieldnames: list[str] | None = None,
) -> None:
    """写入 CSV 文件，自动创建父目录。

    若未提供 fieldnames，则使用第一行字典的 keys（要求 rows 非空）。
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        if not rows:
            raise ValueError("fieldnames must be provided when rows is empty")
        fieldnames = list(rows[0].keys())
    with open(p, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_csv_row(
    path: Path | str,
    headers: list[str],
    row: dict[str, Any],
) -> None:
    """向 CSV 文件追加单行。若文件不存在则自动创建并写入表头。"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    file_exists = p.exists() and p.stat().st_size > 0
    with open(p, "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)
