from __future__ import annotations

import os
from typing import Any

import requests
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, StreamingResponse

from ..models import ChatRequest, ChatResponse
from ..repositories import DEFAULT_TOP_K, DIFY_DEFAULT_TIMEOUT
from ..services import (
    retrieve_citations, match_rule, should_enforce_terminal_rule,
    build_rule_answer, assess_low_confidence, append_low_confidence_followup,
    append_low_confidence_followup_notice, call_dify_lab, call_upstream,
    build_fallback_lab_answer, get_demo_meta, resolve_dify_api_base, build_dify_proxy_auth,
    sanitize_llm_output,
)

router = APIRouter()


@router.post("/api/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    mode = payload.mode if payload.mode in {"agent", "lab"} else "lab"
    question = payload.question.strip()
    citations = retrieve_citations(question, top_k=DEFAULT_TOP_K) if mode == "lab" else []
    rule = match_rule(question) if mode == "lab" else None
    rule_action = str((rule or {}).get("action") or "")
    decision = "llm_answer"
    followup_logged = False

    if rule and should_enforce_terminal_rule(question, rule):
        decision = (
            "rule_blocked"
            if rule_action == "refuse"
            else "emergency_redirect"
            if rule_action == "redirect_emergency"
            else "need_more_info"
        )
        return ChatResponse(
            answer=build_rule_answer(rule, citations),
            mode=mode,
            model="rule-engine",
            decision=decision,
            risk_level=str((rule or {}).get("severity") or ""),
            matched_rule_id=str((rule or {}).get("id") or ""),
            matched_rule_action=rule_action,
            citations=citations,
        )

    low_confidence, low_reason = assess_low_confidence(citations) if mode == "lab" else (False, "")
    if low_confidence:
        decision = "llm_low_confidence"

    guardrail = str((rule or {}).get("response") or "")
    model = "fallback-rule-engine"
    try:
        if mode == "lab":
            answer, model = call_dify_lab(question)
            decision = "llm_answer_guarded" if rule else "llm_answer"
        else:
            answer, model = call_upstream(mode, question, citations, guardrail=guardrail)
    except HTTPException:
        if mode == "lab":
            decision = "llm_fallback_structured"
            answer = build_fallback_lab_answer(question=question, citations=citations, rule=rule, low_confidence_reason=low_reason)
        else:
            raise

    if mode == "lab" and low_confidence:
        followup_logged = append_low_confidence_followup(
            question=question,
            mode=mode,
            decision=decision,
            risk_level=str((rule or {}).get("severity") or ""),
            matched_rule_id=str((rule or {}).get("id") or ""),
            matched_rule_action=rule_action,
            low_confidence_reason=low_reason,
            citations=citations,
        )
        if followup_logged:
            answer = append_low_confidence_followup_notice(answer)

    return ChatResponse(
        answer=answer or "No answer returned.",
        mode=mode,
        model=model,
        decision=decision if not rule else decision,
        risk_level=str((rule or {}).get("severity") or ""),
        matched_rule_id=str((rule or {}).get("id") or ""),
        matched_rule_action=rule_action,
        low_confidence=low_confidence,
        low_confidence_reason=low_reason,
        followup_logged=followup_logged,
        citations=citations,
    )


@router.get("/api/search")
def search(q: str, top_k: int = 5) -> dict[str, Any]:
    query = (q or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="q is required.")
    top_k = max(1, min(10, int(top_k)))
    citations = retrieve_citations(query, top_k=top_k)
    return {"query": query, "count": len(citations), "citations": [item.model_dump() for item in citations]}


@router.get("/v1/parameters")
def dify_parameters_proxy(request: Request) -> Response:
    endpoint = f"{resolve_dify_api_base()}/parameters"
    headers: dict[str, str] = {}
    auth = build_dify_proxy_auth(request)
    if auth:
        headers["Authorization"] = auth

    try:
        upstream = requests.get(endpoint, headers=headers, timeout=(8, 20))
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"dify_proxy_request_failed: {exc}") from exc

    media_type = upstream.headers.get("Content-Type", "application/json")
    return Response(content=upstream.content, status_code=upstream.status_code, media_type=media_type)


@router.post("/v1/chat-messages")
async def dify_chat_messages_proxy(request: Request) -> Response:
    endpoint = f"{resolve_dify_api_base()}/chat-messages"
    timeout = float(os.getenv("DIFY_TIMEOUT", str(DIFY_DEFAULT_TIMEOUT)) or str(DIFY_DEFAULT_TIMEOUT))
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"invalid_json_body: {exc}") from exc

    headers = {"Content-Type": "application/json"}
    auth = build_dify_proxy_auth(request)
    if auth:
        headers["Authorization"] = auth

    try:
        upstream = requests.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=(20, timeout),
            stream=True,
        )
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"dify_proxy_request_failed: {exc}") from exc

    content_type = str(upstream.headers.get("Content-Type", "") or "").lower()
    if "text/event-stream" in content_type:
        def _iter_sse():
            try:
                for chunk in upstream.iter_content(chunk_size=1024):
                    if chunk:
                        yield chunk
            finally:
                upstream.close()

        return StreamingResponse(_iter_sse(), status_code=upstream.status_code, media_type="text/event-stream")

    body = upstream.content
    media_type = upstream.headers.get("Content-Type", "application/json")
    status_code = upstream.status_code
    upstream.close()
    return Response(content=body, status_code=status_code, media_type=media_type)
