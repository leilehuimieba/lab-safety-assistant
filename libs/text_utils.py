"""文本处理工具：归一化、分词等"""
from __future__ import annotations

import re


def normalize_search_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def extract_tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    for chunk in re.findall(r"[a-zA-Z0-9_]+|[\u4e00-\u9fff]+", (text or "").lower()):
        if re.fullmatch(r"[a-zA-Z0-9_]+", chunk):
            if len(chunk) >= 2:
                tokens.add(chunk)
            continue
        if len(chunk) < 2:
            continue
        if len(chunk) <= 8:
            tokens.add(chunk)
        max_ngram = min(4, len(chunk))
        for size in range(2, max_ngram + 1):
            for idx in range(0, len(chunk) - size + 1):
                tokens.add(chunk[idx : idx + size])
    return tokens
