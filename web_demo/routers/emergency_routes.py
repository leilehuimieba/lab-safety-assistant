from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..models import EmergencyCard, EmergencyMatchResponse
from ..repositories import get_emergency_cards
from ..services import to_emergency_card, match_emergency_card

router = APIRouter()


@router.get("/api/emergency/cards", response_model=list[EmergencyCard])
def emergency_cards() -> list[EmergencyCard]:
    return [to_emergency_card(item) for item in get_emergency_cards()]


@router.get("/api/emergency/match", response_model=EmergencyMatchResponse)
def emergency_match(q: str) -> EmergencyMatchResponse:
    query = (q or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="q is required.")
    return match_emergency_card(query)


@router.post("/api/emergency/match", response_model=EmergencyMatchResponse)
def emergency_match_post(payload: dict[str, str]) -> EmergencyMatchResponse:
    query = (payload.get("query") or payload.get("q") or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="query is required.")
    return match_emergency_card(query)
