from __future__ import annotations

"""应急卡片匹配服务

- to_emergency_card: 将原始字典转换为 EmergencyCard 模型
- match_emergency_card: 基于关键词与标题 token 重叠度匹配应急卡片
"""

from typing import Any

from ..models import EmergencyCard, EmergencyMatchResponse
from ..repositories import (
    get_emergency_cards,
    extract_tokens,
    normalize_search_text,
)


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
    query_tokens = extract_tokens(query)
    best_score = 0.0
    best_card: dict[str, Any] | None = None
    for raw in get_emergency_cards():
        keywords = {str(item).lower() for item in raw.get("keywords") or [] if str(item).strip()}
        title_tokens = extract_tokens(str(raw.get("title") or ""))
        card_tokens = keywords | title_tokens
        overlap = len(query_tokens & card_tokens)
        score = float(overlap) + (1.5 if any(token in normalize_search_text(query) for token in keywords) else 0.0)
        if score > best_score:
            best_score = score
            best_card = raw
    return EmergencyMatchResponse(
        query=query,
        matched_card_id=str(best_card.get("id") or "") if best_card else "",
        confidence=round(best_score, 3),
        card=to_emergency_card(best_card) if best_card else None,
    )
