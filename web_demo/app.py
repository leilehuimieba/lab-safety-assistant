from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]


BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent
HTML_FILE = BASE_DIR / "templates" / "index.html"
KB_FILE = REPO_ROOT / "knowledge_base_curated.csv"
RULES_FILE = REPO_ROOT / "safety_rules.yaml"
LOW_CONFIDENCE_QUEUE_FILE = REPO_ROOT / "artifacts" / "low_confidence_followups" / "data_gap_queue.csv"

DEFAULT_BASE_URL = "http://ai.little100.cn:3000/v1"
DEFAULT_MODEL = "gpt-5.2-codex"
DEFAULT_FALLBACK_MODELS = "grok-3-mini,grok-4,grok-3"
DEFAULT_TOP_K = 4
DEFAULT_LOW_CONFIDENCE_TOP_SCORE = 3.5

SEVERITY_SCORE = {"critical": 5, "high": 4, "medium": 3, "low": 2}
TERMINAL_ACTIONS = {"refuse", "redirect_emergency", "ask_for_more_info"}
RISK_LABEL = {1: "低", 2: "低", 3: "中", 4: "高", 5: "极高"}

QUEUE_HEADERS = [
    "created_at",
    "question_hash",
    "question",
    "mode",
    "decision",
    "risk_level",
    "matched_rule_id",
    "matched_rule_action",
    "low_confidence_reason",
    "citation_count",
    "top_score",
    "top_kb_id",
    "top_source_title",
    "suggested_lane",
    "suggested_action",
    "status",
    "notes",
]

SYSTEM_PROMPTS = {
    "agent": "You are a project copilot. Give concise, executable guidance.",
    "lab": (
        "You are a laboratory safety assistant. Output in this order: conclusion, steps, forbidden actions, escalation. "
        "Never provide unsafe or policy-violating instructions."
    ),
}

PPE_HINTS = {
    "护目镜": ["acid", "base", "solvent", "splash", "corrosive", "酸", "碱", "飞溅"],
    "面屏": ["splash", "high pressure", "飞溅", "高压"],
    "耐化学手套": ["acid", "base", "solvent", "corrosive", "hazardous chemical", "酸", "碱", "有机溶剂"],
    "实验服": ["chemical", "biosafety", "reagent", "化学", "生物"],
    "呼吸防护": ["toxic gas", "vapor", "inhalation", "fume", "有毒气体", "蒸气"],
    "低温防护手套": ["liquid nitrogen", "cryogenic", "low temperature", "液氮", "低温"],
    "绝缘手套": ["electric", "shock", "high voltage", "触电", "高压电"],
}

HAZARD_HINTS = {
    "化学": ["acid", "base", "solvent", "corrosive", "hazardous chemical", "酸", "碱", "溶剂", "危化品"],
    "生物安全": ["bio", "pathogen", "sample", "sterilization", "病原", "样本", "灭菌"],
    "电气": ["electric", "shock", "high voltage", "power", "触电", "高压电"],
    "火灾": ["fire", "smoke", "ignition", "burn", "起火", "冒烟", "燃烧"],
    "低温": ["liquid nitrogen", "cryogenic", "frostbite", "液氮", "冻伤"],
    "机械": ["centrifuge", "rotation", "pinch", "moving parts", "离心", "旋转"],
}

_CACHE_LOCK = threading.Lock()
_KB_CACHE: list[dict[str, str]] | None = None
_RULES_CACHE: dict[str, Any] | None = None
_QUEUE_LOCK = threading.Lock()


class ChatRequest(BaseModel):
    mode: str = Field(default="lab", description="agent or lab")
    question: str = Field(min_length=1, max_length=4000)


class RiskAssessRequest(BaseModel):
    scenario: str = Field(min_length=1, max_length=6000)


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
    low_confidence: bool = False
    low_confidence_reason: str = ""
    followup_logged: bool = False
    citations: list[Citation] = Field(default_factory=list)


class RiskAssessResponse(BaseModel):
    scenario: str
    risk_score: int
    risk_level: str
    key_hazards: list[str] = Field(default_factory=list)
    ppe: list[str] = Field(default_factory=list)
    forbidden: list[str] = Field(default_factory=list)
    emergency_actions: list[str] = Field(default_factory=list)
    recommended_steps: list[str] = Field(default_factory=list)
    low_confidence: bool = False
    low_confidence_reason: str = ""
    citations: list[Citation] = Field(default_factory=list)


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def extract_tokens(text: str) -> set[str]:
    chunks = re.findall(r"[a-zA-Z0-9_]+|[\u4e00-\u9fff]+", (text or "").lower())
    tokens: set[str] = set()
    for chunk in chunks:
        if len(chunk) >= 2:
            tokens.add(chunk)
    return tokens


def split_items(text: str) -> list[str]:
    return [x.strip(" -\t") for x in re.split(r"[\n;；。]+", text or "") if x.strip(" -\t")]


def load_kb_entries() -> list[dict[str, str]]:
    if not KB_FILE.exists():
        return []
    rows: list[dict[str, str]] = []
    with KB_FILE.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            blob = normalize_text(
                " ".join(
                    [
                        row.get("title", ""),
                        row.get("question", ""),
                        row.get("answer", ""),
                        row.get("steps", ""),
                        row.get("forbidden", ""),
                        row.get("emergency", ""),
                        row.get("ppe", ""),
                        row.get("hazard_types", ""),
                        row.get("tags", ""),
                    ]
                )
            )
            rows.append(
                {
                    "id": (row.get("id") or "").strip(),
                    "title": (row.get("title") or "").strip(),
                    "source_title": (row.get("source_title") or "").strip(),
                    "source_org": (row.get("source_org") or "").strip(),
                    "source_url": (row.get("source_url") or "").strip(),
                    "risk_level": (row.get("risk_level") or "").strip(),
                    "hazard_types": (row.get("hazard_types") or "").strip(),
                    "answer": (row.get("answer") or "").strip(),
                    "steps": (row.get("steps") or "").strip(),
                    "forbidden": (row.get("forbidden") or "").strip(),
                    "emergency": (row.get("emergency") or "").strip(),
                    "ppe": (row.get("ppe") or "").strip(),
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
        return {"rules": []}
    with RULES_FILE.open("r", encoding="utf-8") as f:
        payload = yaml.safe_load(f) or {}
    if not isinstance(payload, dict):
        return {"rules": []}
    payload.setdefault("rules", [])
    return payload


def get_rules_config() -> dict[str, Any]:
    global _RULES_CACHE
    with _CACHE_LOCK:
        if _RULES_CACHE is None:
            _RULES_CACHE = load_rules_config()
        return _RULES_CACHE


def retrieve_citations(question: str, top_k: int = DEFAULT_TOP_K) -> list[Citation]:
    q = normalize_text(question)
    q_tokens = extract_tokens(question)
    scored: list[tuple[float, dict[str, str]]] = []
    for row in get_kb_entries():
        score = 0.0
        blob = row.get("blob", "")
        for token in q_tokens:
            if token in blob:
                score += 1.0 + min(len(token), 6) * 0.12
        title = normalize_text(row.get("title", ""))
        if title and title in q:
            score += 2.5
        if score > 0:
            scored.append((score, row))
    scored.sort(key=lambda x: x[0], reverse=True)
    selected: list[tuple[float, dict[str, str]]] = scored[:top_k]
    if not selected:
        # Compatibility fallback: keep search usable even when token match is sparse.
        kb_rows = get_kb_entries()
        kb_pref = [row for row in kb_rows if (row.get("id") or "").startswith("KB-")]
        fallback_rows = (kb_pref or kb_rows)[:top_k]
        selected = [(0.1, row) for row in fallback_rows]

    out: list[Citation] = []
    for score, row in selected:
        snippet = " ".join(x for x in [row.get("answer", ""), row.get("steps", ""), row.get("forbidden", "")] if x)[:200]
        out.append(
            Citation(
                kb_id=row.get("id", ""),
                title=row.get("title", ""),
                source_title=row.get("source_title", ""),
                source_org=row.get("source_org", ""),
                source_url=row.get("source_url", ""),
                risk_level=row.get("risk_level", ""),
                snippet=snippet,
                score=round(score, 3),
            )
        )
    return out


def match_rule(question: str) -> dict[str, Any] | None:
    q = normalize_text(question)
    best: dict[str, Any] | None = None
    for order, rule in enumerate(get_rules_config().get("rules") or []):
        if not isinstance(rule, dict):
            continue
        patterns = [str(x).strip() for x in (rule.get("patterns") or []) if str(x).strip()]
        hits = [p for p in patterns if normalize_text(p) in q]
        if not hits:
            continue
        severity = str(rule.get("severity") or "low").lower()
        candidate = {
            "id": str(rule.get("id") or ""),
            "action": str(rule.get("action") or "safe_answer"),
            "severity": severity,
            "response": str(rule.get("response") or ""),
            "score": (SEVERITY_SCORE.get(severity, 1), len(hits), -order),
        }
        if best is None or candidate["score"] > best["score"]:
            best = candidate
    return best


def assess_low_confidence(citations: list[Citation]) -> tuple[bool, str]:
    if not citations:
        return True, "未命中知识库条目|no_kb_match|鏈懡涓?"
    threshold = float(os.getenv("LOW_CONFIDENCE_TOP_SCORE", str(DEFAULT_LOW_CONFIDENCE_TOP_SCORE)))
    if citations[0].score < threshold:
        return True, f"top_score_below_threshold:{citations[0].score}<{threshold}"
    return False, ""


def append_low_confidence_followup(
    *,
    question: str,
    mode: str,
    decision: str,
    risk_level: str,
    matched_rule_id: str,
    matched_rule_action: str,
    low_confidence_reason: str,
    citations: list[Citation],
    queue_file: Path = LOW_CONFIDENCE_QUEUE_FILE,
) -> bool:
    question_norm = normalize_text(question)
    if not question_norm:
        return False
    q_hash = hashlib.sha1(question_norm.encode("utf-8")).hexdigest()
    queue_file = Path(queue_file)
    queue_file.parent.mkdir(parents=True, exist_ok=True)

    with _QUEUE_LOCK:
        existing_hash: set[str] = set()
        if queue_file.exists():
            with queue_file.open("r", encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f):
                    h = (row.get("question_hash") or "").strip()
                    if h:
                        existing_hash.add(h)
        if q_hash in existing_hash:
            return False

        top = citations[0] if citations else None
        payload = {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "question_hash": q_hash,
            "question": question.strip(),
            "mode": mode,
            "decision": decision,
            "risk_level": risk_level,
            "matched_rule_id": matched_rule_id,
            "matched_rule_action": matched_rule_action,
            "low_confidence_reason": low_confidence_reason,
            "citation_count": str(len(citations)),
            "top_score": str(top.score if top else ""),
            "top_kb_id": top.kb_id if top else "",
            "top_source_title": top.source_title if top else "",
            "suggested_lane": "collector",
            "suggested_action": "add_or_rewrite_kb_entry",
            "status": "open",
            "notes": "",
        }

        write_header = not queue_file.exists() or queue_file.stat().st_size == 0
        with queue_file.open("a", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=QUEUE_HEADERS)
            if write_header:
                writer.writeheader()
            writer.writerow(payload)
    return True


def build_rule_answer(rule: dict[str, Any], citations: list[Citation]) -> str:
    response = str(rule.get("response") or "请立即停止高风险操作并联系实验室负责人。").strip()
    citation_lines = (
        "\n".join([f"- {c.kb_id}: {c.title}" for c in citations[:3]]) if citations else "- 暂无直接引用"
    )
    return (
        f"结论：\n{response}\n\n"
        f"缁撹锛?\n{response}\n\n"
        "步骤：\n"
        "1) 立即停止相关操作并隔离风险源。\n"
        "2) 启动本单位SOP与应急流程。\n"
        "3) 按要求佩戴PPE并等待授权人员处置。\n\n"
        "姝ラ锛?\n"
        "1) 立即停止相关操作并隔离风险源。\n"
        "2) 启动本单位SOP与应急流程。\n"
        "3) 按要求佩戴PPE并等待授权人员处置。\n\n"
        "禁止事项：\n"
        "- 禁止继续进行高风险实验。\n"
        "- 禁止绕过审批与防护控制。\n\n"
        "绂佹浜嬮」锛?\n"
        "- 禁止继续进行高风险实验。\n"
        "- 禁止绕过审批与防护控制。\n\n"
        "上报建议：\n"
        "- 立即通知实验室负责人和EHS管理人员。\n"
        f"- 参考依据：\n{citation_lines}\n\n"
        "涓婃姤寤鸿锛?\n"
        "- 立即通知实验室负责人和EHS管理人员。"
    )


def build_system_prompt(mode: str, guardrail: str = "") -> str:
    base = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["lab"])
    return f"{base} Guardrail: {guardrail}".strip() if guardrail else base


def build_user_message(question: str, citations: list[Citation]) -> str:
    if not citations:
        return question
    context = "\n\n".join(
        [
            f"[{i + 1}] {c.kb_id} - {c.title}\nsource: {c.source_title or '-'} | org: {c.source_org or '-'}\nkey: {c.snippet}"
            for i, c in enumerate(citations)
        ]
    )
    return f"Question:\n{question}\n\nKB Context:\n{context}\n\nUse KB first and avoid fabrication."


def call_upstream(mode: str, question: str, citations: list[Citation], guardrail: str = "") -> tuple[str, str]:
    env = {
        "base_url": os.getenv("OPENAI_BASE_URL", DEFAULT_BASE_URL).strip(),
        "api_key": os.getenv("OPENAI_API_KEY", "").strip(),
        "model": os.getenv("OPENAI_MODEL", DEFAULT_MODEL).strip(),
        "fallback": [x.strip() for x in os.getenv("OPENAI_FALLBACK_MODELS", DEFAULT_FALLBACK_MODELS).split(",") if x.strip()],
        "timeout": float(os.getenv("OPENAI_TIMEOUT", "60") or "60"),
    }
    if not env["api_key"]:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is missing.")
    endpoint = env["base_url"].rstrip("/")
    if not endpoint.endswith("/v1"):
        endpoint += "/v1"
    endpoint += "/chat/completions"
    models = [env["model"], *env["fallback"]]
    models = list(dict.fromkeys(models))
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
        }
        try:
            resp = requests.post(endpoint, headers=headers, json=payload, timeout=env["timeout"])
        except requests.RequestException as exc:
            last_error = str(exc)
            continue
        if resp.status_code >= 400:
            last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
            continue
        data = resp.json()
        choices = data.get("choices") or []
        if choices and isinstance(choices[0], dict):
            message = choices[0].get("message") or {}
            content = message.get("content") if isinstance(message, dict) else ""
            if isinstance(content, str) and content.strip():
                return content.strip(), model
        last_error = "empty_response"
    raise HTTPException(status_code=502, detail=f"upstream_failed: {last_error}")


def build_risk_assessment(scenario: str, citations: list[Citation], rule: dict[str, Any] | None) -> RiskAssessResponse:
    severity_score = SEVERITY_SCORE.get(str((rule or {}).get("severity", "")).lower(), 1)
    citation_score = max([int(float(c.risk_level)) for c in citations if str(c.risk_level).replace(".", "", 1).isdigit()] or [1])
    text_norm = normalize_text(scenario)
    keyword_score = 5 if any(x in text_norm for x in ["fire", "shock", "explosion", "leak", "burn", "toxic"]) else 3
    risk_score = max(1, min(5, max(severity_score, citation_score, keyword_score)))

    hazards: set[str] = set()
    for name, words in HAZARD_HINTS.items():
        if any(w in text_norm for w in words):
            hazards.add(name)

    ppe: set[str] = set()
    merged = text_norm + " " + " ".join(c.snippet.lower() for c in citations)
    for name, words in PPE_HINTS.items():
        if any(w in merged for w in words):
            ppe.add(name)

    low_confidence, reason = assess_low_confidence(citations)
    return RiskAssessResponse(
        scenario=scenario,
        risk_score=risk_score,
        risk_level=RISK_LABEL.get(risk_score, "medium"),
        key_hazards=sorted(hazards),
        ppe=sorted(ppe),
        forbidden=[
            "Do not continue high-risk operation without full PPE.",
            "Do not work alone in hazardous procedure.",
            "Do not bypass ventilation, lockout, or approval controls.",
        ],
        emergency_actions=[
            "Stop operation and isolate hazards immediately.",
            "Execute local emergency plan and notify lab supervisor.",
            "Call emergency services when personal injury or fire risk exists.",
        ],
        recommended_steps=[
            "Verify SOP, chemicals, and equipment before starting.",
            "Use buddy check at critical operation points.",
            "Escalate immediately if abnormal smell/smoke/temperature appears.",
        ],
        low_confidence=low_confidence,
        low_confidence_reason=reason,
        citations=citations,
    )


app = FastAPI(title="Lab Safety Assistant Demo", version="0.2.0")


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
    rule = match_rule(question) if mode == "lab" else None
    rule_action = str((rule or {}).get("action") or "")
    decision = "llm_answer"
    if rule and rule_action in TERMINAL_ACTIONS:
        decision = "rule_blocked" if rule_action == "refuse" else "emergency_redirect" if rule_action == "redirect_emergency" else "need_more_info"
        answer = (rule.get("response") or "Operation blocked by safety policy. Please contact supervisor.").strip()
        return ChatResponse(answer=answer, mode=mode, model="rule-engine", decision=decision, citations=citations)

    low_confidence, low_reason = assess_low_confidence(citations) if mode == "lab" else (False, "")
    if low_confidence:
        decision = "llm_low_confidence"
    answer, model = call_upstream(mode, question, citations, guardrail=str((rule or {}).get("response") or ""))
    return ChatResponse(
        answer=answer or "No answer returned.",
        mode=mode,
        model=model,
        decision=decision if not rule else "llm_answer_guarded",
        risk_level=str((rule or {}).get("severity") or ""),
        matched_rule_id=str((rule or {}).get("id") or ""),
        matched_rule_action=rule_action,
        low_confidence=low_confidence,
        low_confidence_reason=low_reason,
        citations=citations,
    )


@app.post("/api/risk_assess", response_model=RiskAssessResponse)
def risk_assess(payload: RiskAssessRequest) -> RiskAssessResponse:
    scenario = payload.scenario.strip()
    if not scenario:
        raise HTTPException(status_code=400, detail="scenario is required.")
    citations = retrieve_citations(scenario, top_k=5)
    return build_risk_assessment(scenario, citations, match_rule(scenario))


@app.get("/api/search")
def search(q: str, top_k: int = 5) -> dict[str, Any]:
    query = (q or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="q is required.")
    top_k = max(1, min(10, int(top_k)))
    citations = retrieve_citations(query, top_k=top_k)
    return {"query": query, "count": len(citations), "citations": [c.model_dump() for c in citations]}
