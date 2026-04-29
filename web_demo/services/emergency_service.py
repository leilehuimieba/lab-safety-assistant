from __future__ import annotations

"""应急卡片匹配服务

- to_emergency_card: 将原始字典转换为 EmergencyCard 模型
- match_emergency_card: 基于关键词 + bge-m3 语义检索混合匹配应急卡片
"""

import os
from typing import Any

from ..models import EmergencyCard, EmergencyMatchResponse
from ..repositories import (
    get_emergency_cards,
    extract_tokens,
    normalize_search_text,
    EMERGENCY_CARDS_FILE,
)

# 语义检索可选依赖
try:
    from libs.embedding_utils import semantic_search

    _EMBEDDING_AVAILABLE = True
except ImportError:  # pragma: no cover
    _EMBEDDING_AVAILABLE = False

_EMBEDDING_CACHE_DIR = EMERGENCY_CARDS_FILE.parent.parent.parent / ".cache" / "embedding_emergency"
_SEMANTIC_WEIGHT = float(os.getenv("EMERGENCY_SEMANTIC_WEIGHT", "6.0"))


def to_emergency_card(raw: dict[str, Any]) -> EmergencyCard:
    return EmergencyCard(
        id=str(raw.get("id") or ""),
        title=str(raw.get("title") or ""),
        category=str(raw.get("category") or ""),
        summary=str(raw.get("summary") or ""),
        trigger_signs=[str(item) for item in raw.get("trigger_signs") or []],
        immediate_actions=[str(item) for item in raw.get("immediate_actions") or []],
        forbidden=[str(item) for item in raw.get("forbidden") or []],
        ppe=[str(item) for item in raw.get("ppe") or []],
        escalation=[str(item) for item in raw.get("escalation") or []],
    )


def match_emergency_card(query: str) -> EmergencyMatchResponse:
    cards = get_emergency_cards()

    # ---- 语义检索（可选） ----
    semantic_scores: dict[str, float] = {}
    if _EMBEDDING_AVAILABLE and cards:
        try:
            mtime = os.path.getmtime(EMERGENCY_CARDS_FILE) if EMERGENCY_CARDS_FILE.exists() else 0.0
            texts = [
                " ".join(
                    [
                        str(raw.get("title", "")),
                        str(raw.get("summary", "")),
                        " ".join(str(item) for item in raw.get("keywords", [])),
                        " ".join(str(item) for item in raw.get("trigger_signs", [])),
                    ]
                )
                for raw in cards
            ]
            semantic_results = semantic_search(
                query=query,
                entries=cards,
                texts=texts,
                cache_dir=_EMBEDDING_CACHE_DIR,
                kb_file_mtime=mtime,
                top_k=2,
            )
            if semantic_results:
                for score, raw in semantic_results:
                    semantic_scores[str(raw.get("id", ""))] = score
        except Exception:
            pass  # fallback 到纯文本匹配

    # ---- 文本匹配（原有逻辑） ----
    query_tokens = extract_tokens(query)
    best_score = 0.0
    best_card: dict[str, Any] | None = None
    for raw in cards:
        keywords = {str(item).lower() for item in raw.get("keywords") or [] if str(item).strip()}
        title_tokens = extract_tokens(str(raw.get("title") or ""))
        card_tokens = keywords | title_tokens
        overlap = len(query_tokens & card_tokens)
        score = float(overlap) + (1.5 if any(token in normalize_search_text(query) for token in keywords) else 0.0)

        # ---- 混合加权：语义分数加成 ----
        sem_score = semantic_scores.get(str(raw.get("id", "")), 0.0)
        if sem_score > 0:
            score += sem_score * _SEMANTIC_WEIGHT

        if score > best_score:
            best_score = score
            best_card = raw
    return EmergencyMatchResponse(
        query=query,
        matched_card_id=str(best_card.get("id") or "") if best_card else "",
        confidence=round(best_score, 3),
        card=to_emergency_card(best_card) if best_card else None,
    )
