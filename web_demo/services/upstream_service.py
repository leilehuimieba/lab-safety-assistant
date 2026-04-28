from __future__ import annotations

"""Dify 与 OpenAI 兼容上游调用服务

- iter_sse_payloads / parse_sse_answer: 解析 Dify SSE 流式响应
- parse_openai_compat_sse: 解析 OpenAI 兼容格式的 SSE 响应
- resolve_dify_api_base / build_dify_proxy_auth: Dify 端点解析与鉴权构建
- call_dify_lab: 调用 Dify 工作流并返回清洗后的回答
- call_upstream: 调用 OpenAI 兼容上游（含故障转移）并返回清洗后的回答
- build_system_prompt / build_user_message: 构建上游对话的 system / user 消息
"""

import json
import os

import requests
from fastapi import HTTPException, Request

from ..models import Citation
from ..repositories import (
    SYSTEM_PROMPTS,
    DIFY_DEFAULT_BASE_URL,
    DIFY_DEFAULT_TIMEOUT,
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    DEFAULT_FALLBACK_MODELS,
)
from .llm_output_service import sanitize_llm_output


def iter_sse_payloads(response: requests.Response) -> list[str]:
    payloads: list[str] = []
    encoding = (response.encoding or "").strip() or "utf-8"
    if encoding.lower() in {"iso-8859-1", "latin-1", "latin1"}:
        encoding = (getattr(response, "apparent_encoding", "") or "").strip() or "utf-8"
    if str(response.headers.get("Content-Type", "") or "").lower().startswith("text/event-stream"):
        encoding = "utf-8"
    for raw in response.iter_lines(decode_unicode=False):
        if not raw:
            continue
        if isinstance(raw, bytes):
            line = raw.decode(encoding, errors="replace").strip()
        else:
            line = str(raw).strip()
        if not line.startswith("data:"):
            continue
        payload = line[5:].lstrip()
        if not payload or payload == "[DONE]":
            continue
        payloads.append(payload)
    return payloads


def parse_sse_answer(response: requests.Response) -> tuple[str, str]:
    answer_parts: list[str] = []
    workflow_status = ""
    workflow_error = ""
    for payload in iter_sse_payloads(response):
        try:
            obj = json.loads(payload)
        except Exception:
            continue
        event = str(obj.get("event") or "").strip().lower()
        if event == "message":
            chunk = str(obj.get("answer") or "").strip()
            if chunk:
                answer_parts.append(chunk)
        elif event == "workflow_finished":
            data = obj.get("data") or {}
            workflow_status = str(data.get("status") or "").strip().lower()
            break
        elif event == "error":
            workflow_error = str(obj.get("message") or obj.get("error") or obj)
            break
    return "".join(answer_parts).strip(), workflow_error or workflow_status


def resolve_dify_api_base() -> str:
    base_url = os.getenv("DIFY_BASE_URL", DIFY_DEFAULT_BASE_URL).strip()
    endpoint = base_url.rstrip("/")
    if not endpoint.endswith("/v1"):
        endpoint += "/v1"
    return endpoint


def build_dify_proxy_auth(request: Request) -> str:
    inbound_auth = (request.headers.get("authorization") or "").strip()
    if inbound_auth:
        return inbound_auth
    app_key = os.getenv("DIFY_APP_API_KEY", "").strip()
    if app_key:
        return f"Bearer {app_key}"
    return ""


def call_dify_lab(question: str) -> tuple[str, str]:
    app_key = os.getenv("DIFY_APP_API_KEY", "").strip()
    timeout = float(os.getenv("DIFY_TIMEOUT", str(DIFY_DEFAULT_TIMEOUT)) or str(DIFY_DEFAULT_TIMEOUT))
    if not app_key:
        raise HTTPException(status_code=500, detail="DIFY_APP_API_KEY is missing.")

    endpoint = f"{resolve_dify_api_base()}/chat-messages"

    try:
        response = requests.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {app_key}",
                "Content-Type": "application/json",
            },
            json={
                "inputs": {},
                "query": question,
                "response_mode": "streaming",
                "conversation_id": "",
                "user": "web-demo-lab",
                "auto_generate_name": False,
            },
            timeout=(20, timeout),
            stream=True,
        )
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"dify_request_failed: {exc}") from exc

    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"dify_http_{response.status_code}: {response.text[:200]}")

    answer, status_text = parse_sse_answer(response)
    if answer:
        return sanitize_llm_output(answer), "dify-workflow"
    raise HTTPException(status_code=502, detail=f"dify_empty_answer: {status_text or 'unknown'}")


def parse_openai_compat_sse(response: requests.Response) -> str:
    parts: list[str] = []
    for payload in iter_sse_payloads(response):
        try:
            obj = json.loads(payload)
        except Exception:
            continue
        choices = obj.get("choices") or []
        if not choices or not isinstance(choices[0], dict):
            continue
        delta = choices[0].get("delta") or {}
        if isinstance(delta, dict):
            content = delta.get("content")
            if isinstance(content, str) and content:
                parts.append(content)
    return "".join(parts).strip()


def build_system_prompt(mode: str, guardrail: str = "") -> str:
    base = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["lab"])
    return f"{base} Guardrail: {guardrail}".strip() if guardrail else base


def build_user_message(question: str, citations: list[Citation]) -> str:
    if not citations:
        return question
    context = "\n\n".join(
        [
            f"[{idx + 1}] {item.kb_id} - {item.title}\n"
            f"source: {item.source_title or '-'} | org: {item.source_org or '-'}\n"
            f"key: {item.snippet}"
            for idx, item in enumerate(citations)
        ]
    )
    return f"Question:\n{question}\n\nKB Context:\n{context}\n\nUse KB first and avoid fabrication."


def call_upstream(mode: str, question: str, citations: list[Citation], guardrail: str = "") -> tuple[str, str]:
    env = {
        "base_url": os.getenv("OPENAI_BASE_URL", DEFAULT_BASE_URL).strip(),
        "api_key": os.getenv("OPENAI_API_KEY", "").strip(),
        "model": os.getenv("OPENAI_MODEL", DEFAULT_MODEL).strip(),
        "fallback": [
            item.strip()
            for item in os.getenv("OPENAI_FALLBACK_MODELS", DEFAULT_FALLBACK_MODELS).split(",")
            if item.strip()
        ],
        "timeout": float(os.getenv("OPENAI_TIMEOUT", "60") or "60"),
    }
    if not env["api_key"]:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is missing.")

    endpoint = env["base_url"].rstrip("/")
    if not endpoint.endswith("/v1"):
        endpoint += "/v1"
    endpoint += "/chat/completions"

    models = list(dict.fromkeys([env["model"], *env["fallback"]]))
    headers = {"Authorization": f"Bearer {env['api_key']}", "Content-Type": "application/json"}
    last_error = "unknown"
    for model in models:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": build_system_prompt(mode, guardrail)},
                {"role": "user", "content": build_user_message(question, citations)},
            ],
            "temperature": 0.2,
            "stream": True,
        }
        try:
            response = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=(20, env["timeout"]),
                stream=True,
            )
        except requests.RequestException as exc:
            last_error = str(exc)
            continue
        if response.status_code >= 400:
            last_error = f"HTTP {response.status_code}: {response.text[:200]}"
            response.close()
            continue
        content_type = str(response.headers.get("Content-Type", "") or "").lower()
        if "text/event-stream" in content_type:
            content = parse_openai_compat_sse(response)
            response.close()
            if content:
                return sanitize_llm_output(content), model
            last_error = "empty_stream_response"
            continue
        try:
            data = response.json()
        finally:
            response.close()
        choices = data.get("choices") or []
        if choices and isinstance(choices[0], dict):
            message = choices[0].get("message") or {}
            content = message.get("content") if isinstance(message, dict) else ""
            if isinstance(content, str) and content.strip():
                return sanitize_llm_output(content), model
        last_error = "empty_response"
    raise HTTPException(status_code=502, detail=f"upstream_failed: {last_error}")
