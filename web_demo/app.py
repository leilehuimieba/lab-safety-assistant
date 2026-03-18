from __future__ import annotations

import csv
import json
import os
import re
import threading
from pathlib import Path
from typing import Any

import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
try:
    import yaml
except ImportError:  # pragma: no cover - optional dependency at import time
    yaml = None  # type: ignore[assignment]


BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent
HTML_FILE = BASE_DIR / "templates" / "index.html"
KB_FILE = REPO_ROOT / "knowledge_base_curated.csv"
RULES_FILE = REPO_ROOT / "safety_rules.yaml"

DEFAULT_BASE_URL = "http://ai.little100.cn:3000/v1"
DEFAULT_MODEL = "gpt-5.2-codex"
DEFAULT_FALLBACK_MODELS = "grok-3-mini,grok-4,grok-3"
DEFAULT_TOP_K = 3

SEVERITY_SCORE = {"critical": 4, "high": 3, "medium": 2, "low": 1}
TERMINAL_ACTIONS = {"refuse", "redirect_emergency", "ask_for_more_info"}

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

EMERGENCY_TEMPLATE_BY_CATEGORY = {
    "chemical_splash_skin": "emergency_chemical_splash_skin",
    "chemical_splash_eye": "emergency_chemical_splash_eye",
    "fire_smoke": "emergency_fire",
    "gas_leak": "emergency_gas_leak",
    "chemical_spill": "emergency_chemical_spill",
    "ingestion": "emergency_ingestion",
    "inhalation": "emergency_inhalation",
    "burn": "emergency_burn",
    "cut_bleeding": "emergency_cut",
}

_CACHE_LOCK = threading.Lock()
_KB_CACHE: list[dict[str, str]] | None = None
_RULES_CACHE: dict[str, Any] | None = None


class ChatRequest(BaseModel):
    mode: str = Field(default="lab", description="agent 或 lab")
    question: str = Field(min_length=1, max_length=4000)


class Citation(BaseModel):
    kb_id: str
    title: str
    source_title: str = ""
    source_org: str = ""
    source_url: str = ""
    risk_level: str = ""
    snippet: str = ""
    score: float = 0.0


class ChatResponse(BaseModel):
    answer: str
    mode: str
    model: str
    decision: str
    risk_level: str = ""
    matched_rule_id: str = ""
    matched_rule_action: str = ""
    citations: list[Citation] = Field(default_factory=list)


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


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def extract_tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    chunks = re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z0-9_]+", text.lower())
    for chunk in chunks:
        if re.fullmatch(r"[a-z0-9_]+", chunk):
            if len(chunk) >= 3:
                tokens.add(chunk)
            continue
        if len(chunk) >= 2:
            if len(chunk) <= 4:
                tokens.add(chunk)
            for n in (2, 3):
                if len(chunk) >= n:
                    for i in range(len(chunk) - n + 1):
                        tokens.add(chunk[i : i + n])
    return tokens


def load_kb_entries() -> list[dict[str, str]]:
    if not KB_FILE.exists():
        return []

    rows: list[dict[str, str]] = []
    with KB_FILE.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            blob_parts = [
                row.get("title", ""),
                row.get("question", ""),
                row.get("answer", ""),
                row.get("steps", ""),
                row.get("forbidden", ""),
                row.get("emergency", ""),
                row.get("tags", ""),
                row.get("hazard_types", ""),
                row.get("source_title", ""),
                row.get("source_org", ""),
            ]
            blob = normalize_text(" ".join(blob_parts))
            rows.append(
                {
                    "id": (row.get("id") or "").strip(),
                    "title": (row.get("title") or "").strip(),
                    "source_title": (row.get("source_title") or "").strip(),
                    "source_org": (row.get("source_org") or "").strip(),
                    "source_url": (row.get("source_url") or "").strip(),
                    "risk_level": (row.get("risk_level") or "").strip(),
                    "answer": (row.get("answer") or "").strip(),
                    "steps": (row.get("steps") or "").strip(),
                    "forbidden": (row.get("forbidden") or "").strip(),
                    "blob": blob,
                }
            )
    return rows


def get_kb_entries() -> list[dict[str, str]]:
    global _KB_CACHE
    with _CACHE_LOCK:
        if _KB_CACHE is None:
            _KB_CACHE = load_kb_entries()
        return _KB_CACHE


def load_rules_config() -> dict[str, Any]:
    if yaml is None or not RULES_FILE.exists():
        return {"rules": [], "safe_response_templates": {}}
    with RULES_FILE.open("r", encoding="utf-8") as f:
        payload = yaml.safe_load(f) or {}
    if not isinstance(payload, dict):
        return {"rules": [], "safe_response_templates": {}}
    payload.setdefault("rules", [])
    payload.setdefault("safe_response_templates", {})
    return payload


def get_rules_config() -> dict[str, Any]:
    global _RULES_CACHE
    with _CACHE_LOCK:
        if _RULES_CACHE is None:
            _RULES_CACHE = load_rules_config()
        return _RULES_CACHE


def _clip(text: str, max_chars: int = 180) -> str:
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars].rstrip()}..."


def retrieve_citations(question: str, top_k: int = DEFAULT_TOP_K) -> list[Citation]:
    kb_rows = get_kb_entries()
    if not kb_rows:
        return []

    q_norm = normalize_text(question)
    q_tokens = extract_tokens(question)
    scored: list[tuple[float, dict[str, str]]] = []

    for row in kb_rows:
        blob = row.get("blob", "")
        score = 0.0
        for token in q_tokens:
            if token and token in blob:
                score += 1.0 + min(len(token), 6) * 0.15
        title = normalize_text(row.get("title", ""))
        if title and title in q_norm:
            score += 3.0
        if score > 0:
            scored.append((score, row))

    scored.sort(key=lambda item: item[0], reverse=True)
    citations: list[Citation] = []
    for score, row in scored[:top_k]:
        snippet_raw = " ".join(
            part
            for part in (row.get("answer", ""), row.get("steps", ""), row.get("forbidden", ""))
            if part
        )
        citations.append(
            Citation(
                kb_id=row.get("id", ""),
                title=row.get("title", ""),
                source_title=row.get("source_title", ""),
                source_org=row.get("source_org", ""),
                source_url=row.get("source_url", ""),
                risk_level=row.get("risk_level", ""),
                snippet=_clip(snippet_raw),
                score=round(score, 3),
            )
        )
    return citations


def build_context_block(citations: list[Citation]) -> str:
    if not citations:
        return ""
    blocks: list[str] = []
    for idx, item in enumerate(citations, start=1):
        lines = [
            f"[{idx}] {item.kb_id} - {item.title}",
            f"来源：{item.source_title or '未标注'} | 机构：{item.source_org or '未标注'}",
            f"要点：{item.snippet or '暂无摘要'}",
        ]
        if item.source_url:
            lines.append(f"链接：{item.source_url}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def match_rule(question: str) -> dict[str, Any] | None:
    config = get_rules_config()
    rules = config.get("rules") or []
    if not rules:
        return None

    q_norm = normalize_text(question)
    best: dict[str, Any] | None = None
    for order, rule in enumerate(rules):
        if not isinstance(rule, dict):
            continue
        patterns = [
            str(item).strip()
            for item in (rule.get("patterns") or [])
            if str(item).strip()
        ]
        hit_patterns = [p for p in patterns if normalize_text(p) in q_norm]
        if not hit_patterns:
            continue

        severity = str(rule.get("severity") or "low").lower()
        candidate = {
            "id": str(rule.get("id") or ""),
            "category": str(rule.get("category") or ""),
            "action": str(rule.get("action") or "safe_answer"),
            "severity": severity,
            "response": str(rule.get("response") or ""),
            "hit_patterns": hit_patterns,
            "score": (
                SEVERITY_SCORE.get(severity, 0),
                len(hit_patterns),
                max(len(v) for v in hit_patterns),
                -order,
            ),
        }
        if best is None or candidate["score"] > best["score"]:
            best = candidate
    return best


def pick_template_text(key: str, fallback: str = "") -> str:
    config = get_rules_config()
    templates = config.get("safe_response_templates") or {}
    value = templates.get(key)
    if isinstance(value, list) and value:
        return str(value[0]).strip()
    if isinstance(value, str):
        return value.strip()
    return fallback


def build_reference_lines(citations: list[Citation]) -> str:
    if not citations:
        return "暂无命中的知识库条目，建议联系实验室老师确认本地制度。"
    lines: list[str] = []
    for idx, item in enumerate(citations, start=1):
        source_name = item.source_title or item.title or item.kb_id
        org = item.source_org or "未标注机构"
        if item.source_url:
            lines.append(f"{idx}. [{item.kb_id}] {source_name}（{org}） {item.source_url}")
        else:
            lines.append(f"{idx}. [{item.kb_id}] {source_name}（{org}）")
    return "\n".join(lines)


def build_rule_answer(rule: dict[str, Any], citations: list[Citation]) -> str:
    action = rule.get("action", "")
    category = rule.get("category", "")
    rule_text = rule.get("response", "").strip()

    if action == "refuse":
        refusal_tip = pick_template_text(
            "refuse",
            "该问题涉及高风险或违规操作，我不能提供具体操作建议。",
        )
        return (
            "结论：\n"
            f"{rule_text or refusal_tip}\n\n"
            "步骤：\n"
            "1. 立即停止当前相关操作，远离可能的危险源。\n"
            "2. 保持现场安全，通知实验室老师或安全管理员。\n"
            "3. 按学校和实验室制度获取正式指导后再处理。\n\n"
            "禁止事项：\n"
            "- 不要继续尝试高风险操作。\n"
            "- 不要绕过PPE、通风、审批和双人复核要求。\n\n"
            "上报建议：\n"
            "- 立即向指导老师/实验室管理员报告。\n\n"
            "参考依据：\n"
            f"{build_reference_lines(citations)}"
        )

    if action == "redirect_emergency":
        template_key = EMERGENCY_TEMPLATE_BY_CATEGORY.get(category, "redirect_emergency")
        emergency_tip = pick_template_text(
            template_key,
            "若出现紧急情况，请立即停止实验并按应急预案处理。",
        )
        return (
            "结论：\n"
            f"{rule_text or emergency_tip}\n\n"
            "步骤：\n"
            "1. 立即停止实验并优先保障人身安全。\n"
            "2. 在确保自身安全的前提下执行断电/断气/隔离等处置。\n"
            "3. 按实验室应急预案处理，必要时联系医疗或119。\n\n"
            "禁止事项：\n"
            "- 不要在没有防护和培训的情况下冒险处置。\n"
            "- 不要单独留在危险区域继续操作。\n\n"
            "上报建议：\n"
            "- 立刻上报指导老师和实验室安全管理员，记录时间、地点和化学品/设备信息。\n\n"
            "参考依据：\n"
            f"{build_reference_lines(citations)}"
        )

    if action == "ask_for_more_info":
        ask_tip = pick_template_text(
            "ask_more_info",
            "请补充具体试剂名称、浓度、设备型号和场景，我才能提供准确建议。",
        )
        return (
            "结论：\n"
            f"{ask_tip}\n\n"
            "步骤：\n"
            "1. 说明实验类型、试剂/设备名称和当前操作步骤。\n"
            "2. 补充风险信号（如异味、冒烟、温度异常、人员症状）。\n"
            "3. 若存在伤害或泄漏，优先按应急流程处置并立即上报。\n\n"
            "禁止事项：\n"
            "- 不要在信息不完整时继续进行高风险操作。\n\n"
            "上报建议：\n"
            "- 若已出现人身伤害或设备异常，先上报再继续咨询。\n\n"
            "参考依据：\n"
            f"{build_reference_lines(citations)}"
        )

    return rule_text


def coerce_text_content(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("text", "content"):
            item = value.get(key)
            if isinstance(item, str):
                return item
        return ""
    if isinstance(value, list):
        chunks: list[str] = []
        for item in value:
            text = coerce_text_content(item)
            if text:
                chunks.append(text)
        return "".join(chunks)
    return ""


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
            piece = coerce_text_content(delta.get("content"))
            if piece:
                answer_parts.append(piece)
        message = first.get("message") or {}
        if isinstance(message, dict):
            msg_content = coerce_text_content(message.get("content"))
            if msg_content:
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
        content = coerce_text_content(message.get("content"))
        if content:
            return content.strip()
    text = coerce_text_content(first.get("text"))
    if text:
        return text.strip()
    return ""


def build_system_prompt(mode: str, guardrail: str = "") -> str:
    base = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["lab"])
    if mode != "lab":
        return base

    extra = (
        "回答必须遵循以下格式：结论、步骤、禁止事项、上报建议。"
        "如果知识库未覆盖，请明确说明不确定并给出保守建议。"
    )
    if guardrail:
        extra += f" 已触发安全提醒：{guardrail}"
    return f"{base}{extra}"


def build_user_message(question: str, context_block: str) -> str:
    if not context_block:
        return question
    return (
        f"用户问题：\n{question}\n\n"
        "知识库片段（优先依据以下内容回答）：\n"
        f"{context_block}\n\n"
        "请不要编造未给出的制度细节。"
    )


def call_upstream(
    mode: str,
    question: str,
    context_block: str = "",
    guardrail: str = "",
) -> tuple[str, str]:
    env = get_env()
    if not env["api_key"]:
        raise HTTPException(
            status_code=500,
            detail="服务端缺少 OPENAI_API_KEY，请先配置部署环境变量。",
        )

    system_prompt = build_system_prompt(mode=mode, guardrail=guardrail)
    user_message = build_user_message(question=question, context_block=context_block)
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
                {"role": "user", "content": user_message},
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
    question = payload.question.strip()
    citations = retrieve_citations(question, top_k=DEFAULT_TOP_K) if mode == "lab" else []
    matched_rule = match_rule(question) if mode == "lab" else None
    decision = "llm_answer"
    risk_level = matched_rule.get("severity", "") if matched_rule else ""
    matched_rule_id = matched_rule.get("id", "") if matched_rule else ""
    matched_rule_action = matched_rule.get("action", "") if matched_rule else ""

    if matched_rule and matched_rule_action in TERMINAL_ACTIONS:
        answer = build_rule_answer(matched_rule, citations)
        model = "rule-engine"
        if matched_rule_action == "refuse":
            decision = "rule_blocked"
        elif matched_rule_action == "redirect_emergency":
            decision = "emergency_redirect"
        else:
            decision = "need_more_info"
    else:
        context_block = build_context_block(citations)
        guardrail = matched_rule.get("response", "") if matched_rule else ""
        answer, model = call_upstream(
            mode=mode,
            question=question,
            context_block=context_block,
            guardrail=guardrail,
        )
        if matched_rule:
            decision = "llm_answer_guarded"

    if not answer:
        answer = "模型未返回文本，请重试。"
    return ChatResponse(
        answer=answer,
        mode=mode,
        model=model,
        decision=decision,
        risk_level=risk_level,
        matched_rule_id=matched_rule_id,
        matched_rule_action=matched_rule_action,
        citations=citations,
    )
