from __future__ import annotations

"""LLM 输出清洗与乱码修复服务

- fix_mojibake_text: 修复被错误解码为 GBK/Latin-1 的 UTF-8 乱码文本
- sanitize_llm_output: 去除思考链标签（<think>、```think）并修复乱码
"""

import re


def fix_mojibake_text(value: str) -> str:
    """Repair UTF-8 text that was accidentally decoded as GBK/Latin-1."""
    text = value or ""
    if not text:
        return text
    # Common path on Windows: UTF-8 bytes were decoded as GBK, producing Àû/½á/Çë-like text.
    if any(marker in text for marker in ["½", "Ç", "Ê", "Ã", "µ", "»", "¼", "£"]):
        try:
            repaired = text.encode("gbk", errors="strict").decode("utf-8", errors="strict")
            if repaired:
                return repaired
        except UnicodeError:
            pass
    # Common path: UTF-8 bytes were decoded as Latin-1, producing ç/è/å-like text.
    if any(marker in text for marker in ["Ã", "Â", "ç", "è", "å"]):
        try:
            repaired = text.encode("latin-1", errors="strict").decode("utf-8", errors="strict")
            if repaired:
                return repaired
        except UnicodeError:
            pass
    return text


def sanitize_llm_output(text: str) -> str:
    cleaned = fix_mojibake_text(text or "")
    cleaned = re.sub(r"<think\b[^>]*>.*?</think>", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"```(?:think|thought|reasoning)[^\n]*\n.*?```", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
    cleaned = cleaned.strip()
    return cleaned or "No answer returned."
