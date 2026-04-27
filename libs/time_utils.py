"""时间处理工具：解析、范围判断等"""
from __future__ import annotations

from datetime import datetime, timedelta


def parse_datetime(value: str) -> datetime | None:
    text = (value or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def within_days(value: str, days: int) -> bool:
    if days <= 0:
        return True
    dt = parse_datetime(value)
    if dt is None:
        return False
    return dt >= datetime.now() - timedelta(days=days)
