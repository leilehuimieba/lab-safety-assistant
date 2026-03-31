from __future__ import annotations

import csv
import hashlib
import json
import os
import random
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

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
EMERGENCY_CARDS_FILE = BASE_DIR / "data" / "emergency_cards.json"
TRAINING_BANK_FILE = BASE_DIR / "data" / "training_question_bank.json"

LOW_CONFIDENCE_QUEUE_FILE = REPO_ROOT / "artifacts" / "low_confidence_followups" / "data_gap_queue.csv"
CHECKLIST_RUNS_FILE = REPO_ROOT / "artifacts" / "checklists" / "checklist_runs.csv"
TRAINING_ATTEMPTS_FILE = REPO_ROOT / "artifacts" / "training" / "training_attempts.csv"
TRAINING_MISTAKES_FILE = REPO_ROOT / "artifacts" / "training" / "training_mistakes.csv"

DEFAULT_BASE_URL = "http://ai.little100.cn:3000/v1"
DEFAULT_MODEL = "gpt-5.2-codex"
DEFAULT_FALLBACK_MODELS = "grok-3-mini,grok-4,grok-3"
DEFAULT_TOP_K = 4
DEFAULT_LOW_CONFIDENCE_TOP_SCORE = 3.5
DEFAULT_TRAINING_PASS_THRESHOLD = 80

SEVERITY_SCORE = {"critical": 5, "high": 4, "medium": 3, "low": 2}
TERMINAL_ACTIONS = {"refuse", "redirect_emergency", "ask_for_more_info"}
RISK_LABEL = {
    1: "Low",
    2: "Medium-Low",
    3: "Medium",
    4: "High",
    5: "Critical",
}

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

CHECKLIST_HEADERS = [
    "record_id",
    "submitted_at",
    "operator",
    "scenario",
    "risk_score",
    "risk_level",
    "key_hazards",
    "allow_start",
    "blocking_reasons",
    "items_json",
    "notes",
]

TRAINING_ATTEMPT_HEADERS = [
    "attempt_id",
    "submitted_at",
    "participant",
    "session_id",
    "score",
    "total_questions",
    "pass_threshold",
    "passed",
    "weak_categories",
]

TRAINING_MISTAKE_HEADERS = [
    "attempt_id",
    "submitted_at",
    "participant",
    "session_id",
    "question_id",
    "category",
    "prompt",
    "selected_indices",
    "correct_indices",
    "references",
]

SYSTEM_PROMPTS = {
    "agent": "You are a project copilot. Give concise, executable guidance.",
    "lab": (
        "You are a laboratory safety assistant. Output in this order: conclusion, steps, forbidden actions, escalation. "
        "Never provide unsafe or policy-violating instructions."
    ),
}

PPE_HINTS = {
    "Splash goggles": ["acid", "base", "solvent", "splash", "corrosive", "etchant"],
    "Face shield": ["splash", "high pressure", "flying debris", "pressurized"],
    "Chemical resistant gloves": ["acid", "base", "solvent", "corrosive", "hazardous chemical"],
    "Lab coat": ["chemical", "biosafety", "reagent", "sample", "hazard"],
    "Respiratory protection": ["toxic gas", "vapor", "inhalation", "fume", "powder"],
    "Cryogenic gloves": ["liquid nitrogen", "cryogenic", "low temperature", "dewars"],
    "Electrical gloves": ["electric", "shock", "high voltage", "live circuit"],
}

HAZARD_HINTS = {
    "Chemical": ["acid", "base", "solvent", "corrosive", "hazardous chemical", "oxidizer", "flammable"],
    "Biosafety": ["bio", "pathogen", "sample", "sterilization", "culture", "blood"],
    "Electrical": ["electric", "shock", "high voltage", "power", "circuit", "battery"],
    "Fire": ["fire", "smoke", "ignition", "burn", "flammable", "reflux"],
    "Cryogenic": ["liquid nitrogen", "cryogenic", "frostbite", "dewars"],
    "Mechanical": ["centrifuge", "rotation", "pinch", "moving parts", "press"],
}

BASE_CHECKLIST_ITEMS = [
    {
        "id": "sop_reviewed",
        "label": "SOP, SDS, and experiment objective have been reviewed.",
        "critical": True,
    },
    {
        "id": "label_verified",
        "label": "Reagent names, concentrations, and labels have been double-checked.",
        "critical": True,
    },
    {
        "id": "ppe_ready",
        "label": "Required PPE is available, correctly worn, and suitable for this task.",
        "critical": True,
    },
    {
        "id": "containment_ready",
        "label": "Ventilation, shielding, or containment controls are available and working.",
        "critical": True,
    },
    {
        "id": "emergency_ready",
        "label": "Emergency shower, eyewash, extinguisher, exits, and contacts are confirmed.",
        "critical": True,
    },
    {
        "id": "waste_route_ready",
        "label": "Waste segregation and temporary storage route are confirmed before start.",
        "critical": False,
    },
]

HAZARD_CHECKLIST_ITEMS = {
    "Chemical": [
        {
            "id": "chemical_incompatibility",
            "label": "Chemical incompatibility, secondary containment, and spill kit are verified.",
            "critical": True,
        }
    ],
    "Biosafety": [
        {
            "id": "biosafety_barrier",
            "label": "Biosafety cabinet, disinfectant, and exposure route controls are ready.",
            "critical": True,
        }
    ],
    "Electrical": [
        {
            "id": "electrical_isolation",
            "label": "Grounding, insulation, and power isolation conditions are confirmed.",
            "critical": True,
        }
    ],
    "Fire": [
        {
            "id": "ignition_control",
            "label": "Ignition sources are controlled and the correct extinguisher is within reach.",
            "critical": True,
        }
    ],
    "Cryogenic": [
        {
            "id": "cryogenic_venting",
            "label": "Vent path, face protection, and oxygen depletion risk controls are confirmed.",
            "critical": True,
        }
    ],
    "Mechanical": [
        {
            "id": "mechanical_guard",
            "label": "Guards, balancing, and moving-part clearance have been checked.",
            "critical": True,
        }
    ],
}

HIGH_RISK_CHECKLIST_ITEMS = [
    {
        "id": "high_risk_authorized",
        "label": "Supervisor approval or buddy check is completed for this high-risk operation.",
        "critical": True,
    },
    {
        "id": "working_alone_control",
        "label": "The task is not being performed alone or an approved escalation path is active.",
        "critical": True,
    },
]

_CACHE_LOCK = threading.Lock()
_QUEUE_LOCK = threading.Lock()
_KB_CACHE: list[dict[str, str]] | None = None
_RULES_CACHE: dict[str, Any] | None = None
_EMERGENCY_CACHE: list[dict[str, Any]] | None = None
_TRAINING_BANK_CACHE: list[dict[str, Any]] | None = None


class ChatRequest(BaseModel):
    mode: str = Field(default="lab", description="agent or lab")
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
    low_confidence: bool = False
    low_confidence_reason: str = ""
    followup_logged: bool = False
    citations: list[Citation] = Field(default_factory=list)


class RiskAssessRequest(BaseModel):
    scenario: str = Field(min_length=1, max_length=6000)


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


class ChecklistGenerateRequest(BaseModel):
    scenario: str = Field(min_length=1, max_length=6000)


class ChecklistItem(BaseModel):
    id: str
    label: str
    critical: bool
    checked: bool = False
    note: str = ""


class ChecklistTemplateResponse(BaseModel):
    scenario: str
    risk_score: int
    risk_level: str
    key_hazards: list[str] = Field(default_factory=list)
    checklist: list[ChecklistItem] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)


class ChecklistSubmitRequest(BaseModel):
    scenario: str = Field(min_length=1, max_length=6000)
    operator: str = Field(default="anonymous", max_length=120)
    notes: str = Field(default="", max_length=1000)
    checklist: list[ChecklistItem] = Field(default_factory=list)


class ChecklistSubmitResponse(BaseModel):
    record_id: str
    submitted_at: str
    scenario: str
    operator: str
    risk_score: int
    risk_level: str
    key_hazards: list[str] = Field(default_factory=list)
    allow_start: bool
    blocking_reasons: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


class EmergencyCard(BaseModel):
    id: str
    title: str
    category: str
    summary: str
    trigger_signs: list[str] = Field(default_factory=list)
    immediate_actions: list[str] = Field(default_factory=list)
    forbidden: list[str] = Field(default_factory=list)
    ppe: list[str] = Field(default_factory=list)
    escalation: list[str] = Field(default_factory=list)


class EmergencyMatchResponse(BaseModel):
    query: str
    matched_card_id: str = ""
    confidence: float = 0.0
    card: EmergencyCard | None = None


class TrainingQuestionPublic(BaseModel):
    id: str
    category: str
    prompt: str
    options: list[str]
    multiple: bool = False
    references: list[str] = Field(default_factory=list)


class TrainingSessionResponse(BaseModel):
    session_id: str
    total_questions: int
    pass_threshold: int
    questions: list[TrainingQuestionPublic] = Field(default_factory=list)


class TrainingAnswer(BaseModel):
    question_id: str
    selected_indices: list[int] = Field(default_factory=list)


class TrainingSubmitRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=120)
    participant: str = Field(default="anonymous", max_length=120)
    answers: list[TrainingAnswer] = Field(default_factory=list)


class TrainingReviewItem(BaseModel):
    question_id: str
    category: str
    prompt: str
    selected_indices: list[int] = Field(default_factory=list)
    correct_indices: list[int] = Field(default_factory=list)
    correct: bool
    explanation: str
    references: list[str] = Field(default_factory=list)


class TrainingSubmitResponse(BaseModel):
    attempt_id: str
    session_id: str
    participant: str
    submitted_at: str
    score: int
    total_questions: int
    pass_threshold: int
    passed: bool
    weak_categories: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    review: list[TrainingReviewItem] = Field(default_factory=list)


class TrainingStatsResponse(BaseModel):
    attempt_count: int
    pass_rate: float
    average_score: float
    latest_submitted_at: str = ""
    category_mistakes: dict[str, int] = Field(default_factory=dict)
    recent_scores: list[int] = Field(default_factory=list)


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def extract_tokens(text: str) -> set[str]:
    chunks = re.findall(r"[a-zA-Z0-9_]+|[\u4e00-\u9fff]+", (text or "").lower())
    return {chunk for chunk in chunks if len(chunk) >= 2}


def write_csv_row(path: Path, headers: list[str], row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def load_json_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def load_kb_entries() -> list[dict[str, str]]:
    if not KB_FILE.exists():
        return []
    rows: list[dict[str, str]] = []
    with KB_FILE.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
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


def get_emergency_cards() -> list[dict[str, Any]]:
    global _EMERGENCY_CACHE
    with _CACHE_LOCK:
        if _EMERGENCY_CACHE is None:
            _EMERGENCY_CACHE = load_json_list(EMERGENCY_CARDS_FILE)
        return _EMERGENCY_CACHE


def get_training_bank() -> list[dict[str, Any]]:
    global _TRAINING_BANK_CACHE
    with _CACHE_LOCK:
        if _TRAINING_BANK_CACHE is None:
            _TRAINING_BANK_CACHE = load_json_list(TRAINING_BANK_FILE)
        return _TRAINING_BANK_CACHE


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
        title_norm = normalize_text(row.get("title", ""))
        if title_norm and title_norm in q:
            score += 2.5
        if score > 0:
            scored.append((score, row))
    scored.sort(key=lambda item: item[0], reverse=True)
    selected = scored[: max(1, top_k)]
    if not selected:
        selected = [(0.1, row) for row in get_kb_entries()[: max(1, top_k)]]

    citations: list[Citation] = []
    for score, row in selected:
        snippet = " ".join(
            part for part in [row.get("answer", ""), row.get("steps", ""), row.get("forbidden", "")] if part
        )[:220]
        citations.append(
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
    return citations


def match_rule(question: str) -> dict[str, Any] | None:
    q = normalize_text(question)
    best: dict[str, Any] | None = None
    for order, rule in enumerate(get_rules_config().get("rules") or []):
        if not isinstance(rule, dict):
            continue
        patterns = [str(item).strip() for item in (rule.get("patterns") or []) if str(item).strip()]
        hits = [pattern for pattern in patterns if normalize_text(pattern) in q]
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
        return True, "no_kb_match"
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
    question_hash = hashlib.sha1(question_norm.encode("utf-8")).hexdigest()
    queue_file.parent.mkdir(parents=True, exist_ok=True)

    with _QUEUE_LOCK:
        existing_hashes: set[str] = set()
        if queue_file.exists():
            with queue_file.open("r", encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f):
                    value = (row.get("question_hash") or "").strip()
                    if value:
                        existing_hashes.add(value)
        if question_hash in existing_hashes:
            return False

        top = citations[0] if citations else None
        write_csv_row(
            queue_file,
            QUEUE_HEADERS,
            {
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "question_hash": question_hash,
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
            },
        )
    return True


def format_citation_lines(citations: list[Citation], limit: int = 3) -> str:
    if not citations:
        return "- no direct KB citation"
    return "\n".join(f"- {item.kb_id}: {item.source_title or item.title or '-'}" for item in citations[:limit])


def build_rule_answer(rule: dict[str, Any], citations: list[Citation]) -> str:
    response = str(rule.get("response") or "Stop the task and follow the local emergency procedure immediately.").strip()
    return (
        "Conclusion:\n"
        f"{response}\n\n"
        "Steps:\n"
        "1. Stop the current action and isolate the hazard source.\n"
        "2. Notify the laboratory supervisor and safety contact immediately.\n"
        "3. Follow the local SOP for scene control, reporting, and documentation.\n\n"
        "Forbidden actions:\n"
        "- Do not continue the high-risk operation.\n"
        "- Do not bypass ventilation, approvals, interlocks, or PPE requirements.\n\n"
        "Escalation:\n"
        "- If there is injury, fire, leak, or exposure risk, trigger the emergency plan at once.\n\n"
        "References:\n"
        f"{format_citation_lines(citations)}"
    )


def build_fallback_lab_answer(
    question: str,
    citations: list[Citation],
    rule: dict[str, Any] | None = None,
    low_confidence_reason: str = "",
) -> str:
    highest_risk = max(
        [int(float(item.risk_level)) for item in citations if str(item.risk_level).replace(".", "", 1).isdigit()] or [3]
    )
    risk_text = RISK_LABEL.get(highest_risk, "Medium")
    top_title = citations[0].title if citations else "No direct KB match"
    notes = low_confidence_reason or "upstream unavailable"
    guard = str((rule or {}).get("response") or "").strip()
    return (
        "Conclusion:\n"
        f"Treat this as a {risk_text} laboratory safety scenario. Use the local SOP and escalate early instead of improvising.\n\n"
        "Steps:\n"
        "1. Pause the operation and isolate energy, reaction, or exposure sources.\n"
        "2. Re-check PPE, containment, ventilation, and emergency equipment.\n"
        "3. Follow the written SOP and assign one person to control, one person to observe, and one person to report.\n"
        "4. If injury, fire, leak, or abnormal reaction exists, trigger the emergency plan immediately.\n\n"
        "Forbidden actions:\n"
        "- Do not continue without authorization or supervision.\n"
        "- Do not bypass ventilation, lockout, shielding, or waste segregation controls.\n"
        "- Do not hide abnormal events or delay reporting.\n\n"
        "Escalation:\n"
        "- Injury or exposure: rinse/isolate and contact medical support.\n"
        "- Fire or explosion risk: evacuate and call emergency responders.\n"
        "- Spill or leak: cordon off the area and follow the spill SOP.\n\n"
        "References:\n"
        f"- top context: {top_title}\n"
        f"{format_citation_lines(citations)}\n\n"
        "Notes:\n"
        f"- fallback reason: {notes}\n"
        f"- guardrail: {guard or 'N/A'}\n"
        f"- original question: {question.strip()}"
    )


def append_low_confidence_followup_notice(answer: str) -> str:
    note = "Note: this question has been added to the low-confidence follow-up queue for later KB improvement."
    text = (answer or "").strip()
    if not text or note in text:
        return text or note
    return f"{text}\n\n{note}"


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
        }
        try:
            response = requests.post(endpoint, headers=headers, json=payload, timeout=env["timeout"])
        except requests.RequestException as exc:
            last_error = str(exc)
            continue
        if response.status_code >= 400:
            last_error = f"HTTP {response.status_code}: {response.text[:200]}"
            continue
        data = response.json()
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
    citation_score = max(
        [int(float(item.risk_level)) for item in citations if str(item.risk_level).replace(".", "", 1).isdigit()] or [1]
    )
    text_norm = normalize_text(scenario)
    keyword_score = 5 if any(word in text_norm for word in ["fire", "shock", "explosion", "leak", "burn", "toxic"]) else 3
    risk_score = max(1, min(5, max(severity_score, citation_score, keyword_score)))

    hazards: set[str] = set()
    for hazard, words in HAZARD_HINTS.items():
        if any(word in text_norm for word in words):
            hazards.add(hazard)

    ppe: set[str] = set()
    merged = text_norm + " " + " ".join(item.snippet.lower() for item in citations)
    for ppe_name, words in PPE_HINTS.items():
        if any(word in merged for word in words):
            ppe.add(ppe_name)

    low_confidence, reason = assess_low_confidence(citations)
    return RiskAssessResponse(
        scenario=scenario,
        risk_score=risk_score,
        risk_level=RISK_LABEL.get(risk_score, "Medium"),
        key_hazards=sorted(hazards),
        ppe=sorted(ppe),
        forbidden=[
            "Do not continue a hazardous task without PPE and supervisor alignment.",
            "Do not work alone during high-risk or unfamiliar procedures.",
            "Do not bypass ventilation, shielding, lockout, or approval controls.",
        ],
        emergency_actions=[
            "Stop the task and isolate the hazard source immediately.",
            "Notify the local supervisor and execute the emergency plan.",
            "Call emergency responders if there is injury, exposure, or fire risk.",
        ],
        recommended_steps=[
            "Verify SOP, chemicals, equipment, and waste route before starting.",
            "Use a buddy check at critical operation points.",
            "Escalate immediately if abnormal odor, smoke, heat, or pressure appears.",
        ],
        low_confidence=low_confidence,
        low_confidence_reason=reason,
        citations=citations,
    )


def dedupe_checklist_items(items: list[dict[str, Any]]) -> list[ChecklistItem]:
    seen: set[str] = set()
    deduped: list[ChecklistItem] = []
    for item in items:
        item_id = str(item.get("id") or "").strip()
        if not item_id or item_id in seen:
            continue
        seen.add(item_id)
        deduped.append(
            ChecklistItem(
                id=item_id,
                label=str(item.get("label") or "").strip(),
                critical=bool(item.get("critical")),
            )
        )
    return deduped


def build_checklist_template(scenario: str) -> ChecklistTemplateResponse:
    citations = retrieve_citations(scenario, top_k=5)
    assessment = build_risk_assessment(scenario, citations, match_rule(scenario))
    items = list(BASE_CHECKLIST_ITEMS)
    for hazard in assessment.key_hazards:
        items.extend(HAZARD_CHECKLIST_ITEMS.get(hazard, []))
    if assessment.risk_score >= 4:
        items.extend(HIGH_RISK_CHECKLIST_ITEMS)
    if not assessment.key_hazards:
        items.append(
            {
                "id": "scope_defined",
                "label": "The scope, materials, and operating boundary are clear before starting.",
                "critical": True,
            }
        )
    return ChecklistTemplateResponse(
        scenario=scenario,
        risk_score=assessment.risk_score,
        risk_level=assessment.risk_level,
        key_hazards=assessment.key_hazards,
        checklist=dedupe_checklist_items(items),
        recommended_actions=assessment.recommended_steps,
        citations=assessment.citations,
    )


def evaluate_checklist_submission(payload: ChecklistSubmitRequest) -> ChecklistSubmitResponse:
    template = build_checklist_template(payload.scenario)
    submitted_items = {item.id: item for item in payload.checklist}
    checked_items: list[ChecklistItem] = []
    blocking: list[str] = []

    for base_item in template.checklist:
        current = submitted_items.get(base_item.id)
        item = ChecklistItem(
            id=base_item.id,
            label=base_item.label,
            critical=base_item.critical,
            checked=bool(current.checked) if current else False,
            note=current.note if current else "",
        )
        checked_items.append(item)
        if item.critical and not item.checked:
            blocking.append(item.label)

    allow_start = not blocking
    next_actions = (
        ["Checklist passed. Start only under the defined SOP and continue to monitor abnormalities."]
        if allow_start
        else [
            "Do not start the task yet.",
            "Complete all unchecked critical items.",
            "Escalate to supervisor if any critical item cannot be satisfied.",
        ]
    )
    record_id = f"CHK-{datetime.now().strftime('%Y%m%d')}-{uuid4().hex[:8]}"
    submitted_at = datetime.now().isoformat(timespec="seconds")
    write_csv_row(
        CHECKLIST_RUNS_FILE,
        CHECKLIST_HEADERS,
        {
            "record_id": record_id,
            "submitted_at": submitted_at,
            "operator": payload.operator.strip() or "anonymous",
            "scenario": payload.scenario.strip(),
            "risk_score": template.risk_score,
            "risk_level": template.risk_level,
            "key_hazards": "|".join(template.key_hazards),
            "allow_start": str(allow_start).lower(),
            "blocking_reasons": " | ".join(blocking),
            "items_json": json.dumps([item.model_dump() for item in checked_items], ensure_ascii=False),
            "notes": payload.notes.strip(),
        },
    )
    return ChecklistSubmitResponse(
        record_id=record_id,
        submitted_at=submitted_at,
        scenario=payload.scenario,
        operator=payload.operator,
        risk_score=template.risk_score,
        risk_level=template.risk_level,
        key_hazards=template.key_hazards,
        allow_start=allow_start,
        blocking_reasons=blocking,
        next_actions=next_actions,
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
        score = float(overlap) + (1.5 if any(token in normalize_text(query) for token in keywords) else 0.0)
        if score > best_score:
            best_score = score
            best_card = raw
    return EmergencyMatchResponse(
        query=query,
        matched_card_id=str(best_card.get("id") or "") if best_card else "",
        confidence=round(best_score, 3),
        card=to_emergency_card(best_card) if best_card else None,
    )


def to_public_question(raw: dict[str, Any]) -> TrainingQuestionPublic:
    return TrainingQuestionPublic(
        id=str(raw.get("id") or ""),
        category=str(raw.get("category") or ""),
        prompt=str(raw.get("prompt") or ""),
        options=[str(item) for item in raw.get("options") or []],
        multiple=bool(raw.get("multiple")),
        references=[str(item) for item in raw.get("references") or []],
    )


def get_training_questions(limit: int) -> list[dict[str, Any]]:
    bank = get_training_bank()
    if not bank:
        return []
    limit = max(1, min(limit, len(bank)))
    return random.sample(bank, limit)


def grade_training_submit(payload: TrainingSubmitRequest) -> TrainingSubmitResponse:
    bank = {str(item.get("id") or ""): item for item in get_training_bank()}
    if not bank:
        raise HTTPException(status_code=500, detail="training bank is empty.")

    submitted_at = datetime.now().isoformat(timespec="seconds")
    attempt_id = f"TRN-{datetime.now().strftime('%Y%m%d')}-{uuid4().hex[:8]}"
    answers_by_id = {item.question_id: sorted(set(item.selected_indices)) for item in payload.answers}

    review: list[TrainingReviewItem] = []
    wrong_categories: list[str] = []
    correct_count = 0

    for question_id, selected in answers_by_id.items():
        raw = bank.get(question_id)
        if not raw:
            continue
        correct_indices = sorted(int(idx) for idx in raw.get("correct_indices") or [])
        is_correct = selected == correct_indices
        if is_correct:
            correct_count += 1
        else:
            wrong_categories.append(str(raw.get("category") or "Uncategorized"))
            write_csv_row(
                TRAINING_MISTAKES_FILE,
                TRAINING_MISTAKE_HEADERS,
                {
                    "attempt_id": attempt_id,
                    "submitted_at": submitted_at,
                    "participant": payload.participant.strip() or "anonymous",
                    "session_id": payload.session_id,
                    "question_id": question_id,
                    "category": str(raw.get("category") or ""),
                    "prompt": str(raw.get("prompt") or ""),
                    "selected_indices": json.dumps(selected, ensure_ascii=False),
                    "correct_indices": json.dumps(correct_indices, ensure_ascii=False),
                    "references": " | ".join(str(item) for item in raw.get("references") or []),
                },
            )
        review.append(
            TrainingReviewItem(
                question_id=question_id,
                category=str(raw.get("category") or ""),
                prompt=str(raw.get("prompt") or ""),
                selected_indices=selected,
                correct_indices=correct_indices,
                correct=is_correct,
                explanation=str(raw.get("explanation") or ""),
                references=[str(item) for item in raw.get("references") or []],
            )
        )

    total_questions = len(review)
    score = int(round((correct_count / total_questions) * 100)) if total_questions else 0
    pass_threshold = int(os.getenv("TRAINING_PASS_THRESHOLD", str(DEFAULT_TRAINING_PASS_THRESHOLD)) or "80")
    passed = score >= pass_threshold
    weak_categories = sorted(set(wrong_categories))

    write_csv_row(
        TRAINING_ATTEMPTS_FILE,
        TRAINING_ATTEMPT_HEADERS,
        {
            "attempt_id": attempt_id,
            "submitted_at": submitted_at,
            "participant": payload.participant.strip() or "anonymous",
            "session_id": payload.session_id,
            "score": score,
            "total_questions": total_questions,
            "pass_threshold": pass_threshold,
            "passed": str(passed).lower(),
            "weak_categories": " | ".join(weak_categories),
        },
    )

    recommended_actions = (
        ["Training passed. Review the explanations once and continue to scenario drills."]
        if passed
        else [
            "Review all incorrect questions and linked references.",
            "Repeat the quiz after updating weak categories.",
            "Do not approve independent high-risk work until the pass threshold is met.",
        ]
    )
    return TrainingSubmitResponse(
        attempt_id=attempt_id,
        session_id=payload.session_id,
        participant=payload.participant,
        submitted_at=submitted_at,
        score=score,
        total_questions=total_questions,
        pass_threshold=pass_threshold,
        passed=passed,
        weak_categories=weak_categories,
        recommended_actions=recommended_actions,
        review=review,
    )


def load_training_stats() -> TrainingStatsResponse:
    attempts: list[dict[str, str]] = []
    mistakes: dict[str, int] = {}
    latest_submitted_at = ""

    if TRAINING_ATTEMPTS_FILE.exists():
        with TRAINING_ATTEMPTS_FILE.open("r", encoding="utf-8-sig", newline="") as f:
            attempts = [row for row in csv.DictReader(f)]
    if TRAINING_MISTAKES_FILE.exists():
        with TRAINING_MISTAKES_FILE.open("r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                category = (row.get("category") or "Uncategorized").strip() or "Uncategorized"
                mistakes[category] = mistakes.get(category, 0) + 1

    scores = [int(float(row.get("score", "0") or "0")) for row in attempts]
    passed_count = sum(1 for row in attempts if (row.get("passed") or "").strip().lower() == "true")
    if attempts:
        latest_submitted_at = attempts[-1].get("submitted_at", "") or ""

    return TrainingStatsResponse(
        attempt_count=len(attempts),
        pass_rate=round((passed_count / len(attempts)) if attempts else 0.0, 4),
        average_score=round((sum(scores) / len(scores)) if scores else 0.0, 2),
        latest_submitted_at=latest_submitted_at,
        category_mistakes=dict(sorted(mistakes.items(), key=lambda item: item[1], reverse=True)[:5]),
        recent_scores=scores[-10:],
    )


app = FastAPI(title="Lab Safety Assistant Demo", version="0.4.0")


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
    followup_logged = False

    if rule and rule_action in TERMINAL_ACTIONS:
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
        decision=decision if not rule else "llm_answer_guarded",
        risk_level=str((rule or {}).get("severity") or ""),
        matched_rule_id=str((rule or {}).get("id") or ""),
        matched_rule_action=rule_action,
        low_confidence=low_confidence,
        low_confidence_reason=low_reason,
        followup_logged=followup_logged,
        citations=citations,
    )


@app.post("/api/risk_assess", response_model=RiskAssessResponse)
def risk_assess(payload: RiskAssessRequest) -> RiskAssessResponse:
    scenario = payload.scenario.strip()
    if not scenario:
        raise HTTPException(status_code=400, detail="scenario is required.")
    citations = retrieve_citations(scenario, top_k=5)
    return build_risk_assessment(scenario, citations, match_rule(scenario))


@app.post("/api/checklist/template", response_model=ChecklistTemplateResponse)
def checklist_template(payload: ChecklistGenerateRequest) -> ChecklistTemplateResponse:
    return build_checklist_template(payload.scenario.strip())


@app.post("/api/checklist/submit", response_model=ChecklistSubmitResponse)
def checklist_submit(payload: ChecklistSubmitRequest) -> ChecklistSubmitResponse:
    if not payload.checklist:
        raise HTTPException(status_code=400, detail="checklist is required.")
    return evaluate_checklist_submission(payload)


@app.get("/api/emergency/cards", response_model=list[EmergencyCard])
def emergency_cards() -> list[EmergencyCard]:
    return [to_emergency_card(item) for item in get_emergency_cards()]


@app.get("/api/emergency/match", response_model=EmergencyMatchResponse)
def emergency_match(q: str) -> EmergencyMatchResponse:
    query = (q or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="q is required.")
    return match_emergency_card(query)


@app.get("/api/training/questions", response_model=TrainingSessionResponse)
def training_questions(limit: int = 5) -> TrainingSessionResponse:
    questions = get_training_questions(limit)
    if not questions:
        raise HTTPException(status_code=500, detail="training bank is empty.")
    session_id = f"SESSION-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:6]}"
    pass_threshold = int(os.getenv("TRAINING_PASS_THRESHOLD", str(DEFAULT_TRAINING_PASS_THRESHOLD)) or "80")
    return TrainingSessionResponse(
        session_id=session_id,
        total_questions=len(questions),
        pass_threshold=pass_threshold,
        questions=[to_public_question(item) for item in questions],
    )


@app.post("/api/training/submit", response_model=TrainingSubmitResponse)
def training_submit(payload: TrainingSubmitRequest) -> TrainingSubmitResponse:
    if not payload.answers:
        raise HTTPException(status_code=400, detail="answers are required.")
    return grade_training_submit(payload)


@app.get("/api/training/stats", response_model=TrainingStatsResponse)
def training_stats() -> TrainingStatsResponse:
    return load_training_stats()


@app.get("/api/search")
def search(q: str, top_k: int = 5) -> dict[str, Any]:
    query = (q or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="q is required.")
    top_k = max(1, min(10, int(top_k)))
    citations = retrieve_citations(query, top_k=top_k)
    return {"query": query, "count": len(citations), "citations": [item.model_dump() for item in citations]}
