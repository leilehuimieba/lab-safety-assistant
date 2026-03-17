from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field


BASE_DIR = Path(__file__).resolve().parent
HTML_FILE = BASE_DIR / "templates" / "index.html"

DEFAULT_BASE_URL = "http://ai.little100.cn:3000/v1"
DEFAULT_MODEL = "gpt-5.2-codex"
DEFAULT_FALLBACK_MODELS = "grok-3-mini,grok-4,grok-3"

SYSTEM_PROMPTS = {
    "agent": (
        "你是项目协作智能体。目标是帮助高校项目组高效推进任务，回答要结构化、可执行、可落地。"
        "如果信息不足，先明确假设，再给出下一步操作建议。"
    ),
    "lab": (
        "你是实验室安全小助手。你必须优先强调安全边界和应急优先级。"
        "回答请给出：1)结论 2)步骤 3)禁止事项 4)何时上报老师/管理员。"
        "不要提供鼓励违规或危险操作的建议。"
    ),
}


class ChatRequest(BaseModel):
    mode: str = Field(default="lab", description="agent 或 lab")
    question: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    answer: str
    mode: str
    model: str


def get_env() -> dict[str, str]:
    base_url = os.getenv("OPENAI_BASE_URL", DEFAULT_BASE_URL).strip()
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL).strip()
    timeout_s = os.getenv("OPENAI_TIMEOUT", "60").strip()
    fallback_models = os.getenv("OPENAI_FALLBACK_MODELS", DEFAULT_FALLBACK_MODELS).strip()
    return {
        "base_url": base_url,
        "api_key": api_key,
        "model": model,
        "timeout_s": timeout_s,
        "fallback_models": fallback_models,
    }


def resolve_endpoint(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/v1"):
        return f"{normalized}/chat/completions"
    return f"{normalized}/v1/chat/completions"


def parse_sse_answer(response: requests.Response) -> str:
    answer_parts: list[str] = []
    for line in response.iter_lines(decode_unicode=False):
        if not line:
            continue
        if not line.startswith(b"data:"):
            continue
        payload = line[5:].strip()
        if payload == b"[DONE]":
            break
        try:
            obj = json.loads(payload.decode("utf-8", errors="ignore"))
        except json.JSONDecodeError:
            continue
        choices = obj.get("choices") or []
        if not choices:
            continue
        first = choices[0] if isinstance(choices[0], dict) else {}
        delta = first.get("delta") or {}
        if isinstance(delta, dict):
            piece = delta.get("content")
            if isinstance(piece, str):
                answer_parts.append(piece)
        message = first.get("message") or {}
        if isinstance(message, dict):
            msg_content = message.get("content")
            if isinstance(msg_content, str):
                answer_parts.append(msg_content)
    return "".join(answer_parts).strip()


def parse_json_answer(response: requests.Response) -> str:
    data = response.json()
    choices = data.get("choices") or []
    if not choices:
        return ""
    first = choices[0] if isinstance(choices[0], dict) else {}
    message = first.get("message") or {}
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str):
            return content.strip()
    text = first.get("text")
    if isinstance(text, str):
        return text.strip()
    return ""


def call_upstream(mode: str, question: str) -> tuple[str, str]:
    env = get_env()
    if not env["api_key"]:
        raise HTTPException(
            status_code=500,
            detail="服务端缺少 OPENAI_API_KEY，请先配置部署环境变量。",
        )

    system_prompt = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["lab"])
    endpoint = resolve_endpoint(env["base_url"])

    preferred_model = env["model"]
    fallback_models = [m.strip() for m in env["fallback_models"].split(",") if m.strip()]
    candidate_models: list[str] = []
    for model in [preferred_model, *fallback_models]:
        if model not in candidate_models:
            candidate_models.append(model)

    headers = {
        "Authorization": f"Bearer {env['api_key']}",
        "Content-Type": "application/json",
    }

    try:
        timeout = float(env["timeout_s"])
    except ValueError:
        timeout = 60.0

    last_error = "unknown_error"

    for model in candidate_models:
        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
            "temperature": 0.2,
            "stream": True,
        }

        try:
            response = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=timeout,
                stream=True,
            )
        except requests.RequestException as exc:
            last_error = f"上游请求失败: {exc}"
            continue

        if response.status_code >= 400:
            text = response.text[:500]
            last_error = f"HTTP {response.status_code} {text}"
            # 中转站经常返回 model_not_found，允许自动回退到备用模型。
            if "model_not_found" in text:
                continue
            continue

        content_type = (response.headers.get("content-type") or "").lower()
        answer = ""
        try:
            if "text/event-stream" in content_type:
                answer = parse_sse_answer(response)
            else:
                answer = parse_json_answer(response)
        except Exception as exc:  # noqa: BLE001
            last_error = f"解析上游响应失败: {exc}"
            continue

        if answer:
            return answer, model
        last_error = f"模型 {model} 返回空文本"

    raise HTTPException(status_code=502, detail=f"上游调用失败：{last_error}")


app = FastAPI(title="实验室安全小助手在线演示", version="0.1.0")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(HTML_FILE)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    mode = payload.mode if payload.mode in {"agent", "lab"} else "lab"
    answer, model = call_upstream(mode=mode, question=payload.question.strip())
    if not answer:
        answer = "模型未返回文本，请重试。"
    return ChatResponse(answer=answer, mode=mode, model=model)
