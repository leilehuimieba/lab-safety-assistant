from __future__ import annotations

import csv
import json
import os
import re
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from libs.common_io import load_json_list, write_csv_row
from libs.text_utils import normalize_search_text, extract_tokens
from libs.time_utils import parse_datetime, within_days

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]


BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent
HTML_FILE = BASE_DIR / "frontend" / "dist" / "index.html"
KB_FILE = REPO_ROOT / "knowledge_base_curated.csv"
RULES_FILE = REPO_ROOT / "safety_rules.yaml"
EMERGENCY_CARDS_FILE = BASE_DIR / "data" / "emergency_cards.json"
TRAINING_BANK_FILE = BASE_DIR / "data" / "training_question_bank.json"

LOW_CONFIDENCE_QUEUE_FILE = REPO_ROOT / "artifacts" / "low_confidence_followups" / "data_gap_queue.csv"
CHECKLIST_RUNS_FILE = REPO_ROOT / "artifacts" / "checklists" / "checklist_runs.csv"
TRAINING_ATTEMPTS_FILE = REPO_ROOT / "artifacts" / "training" / "training_attempts.csv"
TRAINING_MISTAKES_FILE = REPO_ROOT / "artifacts" / "training" / "training_mistakes.csv"
INCIDENT_REVIEWS_FILE = REPO_ROOT / "artifacts" / "incidents" / "incident_reviews.csv"

DEFAULT_BASE_URL = "http://ai.little100.cn:3000/v1"
DEFAULT_MODEL = "gpt-5.2-codex"
DEFAULT_FALLBACK_MODELS = "grok-3-mini,grok-4,grok-3"
DEFAULT_TOP_K = 4
DEFAULT_LOW_CONFIDENCE_TOP_SCORE = 3.5
DEFAULT_TRAINING_PASS_THRESHOLD = 80
APP_VERSION = "defense-freeze-20260331"
FORMAL_EVAL_SCORE = "20/20"
STABILITY_EVIDENCE = "3/3 PASS"
KB_IMPORT_SUCCESS_COUNT = 398
DIFY_DEFAULT_BASE_URL = "http://127.0.0.1:8080"
DIFY_DEFAULT_TIMEOUT = 120.0

SEVERITY_SCORE = {"critical": 5, "high": 4, "medium": 3, "low": 2}
TERMINAL_ACTIONS = {"refuse", "redirect_emergency", "ask_for_more_info"}
REFUSE_INTENT_MARKERS = [
    "能不能",
    "可不可以",
    "可以吗",
    "绕过",
    "规避",
    "跳过",
    "怎么混",
    "混吗",
    "一起混",
    "直接倒",
    "倒掉",
    "下水道",
    "明火",
    "酒精灯",
    "加热",
    "不开通风柜",
    "不用通风",
    "不戴",
    "省略ppe",
    "直接开",
    "运转时开盖",
]
EMERGENCY_INTENT_MARKERS = [
    "怎么办",
    "怎么处理",
    "如何处理",
    "第一步",
    "应急",
    "事故",
    "紧急",
    "受伤",
    "泄漏",
    "起火",
    "着火",
    "冒烟",
    "暴露",
]
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
    "review_status",
    "reviewed_by",
    "reviewed_at",
    "review_comment",
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

INCIDENT_HEADERS = [
    "incident_id",
    "reported_at",
    "updated_at",
    "reporter",
    "title",
    "scenario",
    "severity",
    "status",
    "location",
    "cause_categories",
    "immediate_actions",
    "corrective_actions",
    "owner",
    "due_date",
    "closure_notes",
]

INCIDENT_STATUS_ORDER = {"open": 1, "in_review": 2, "action_in_progress": 3, "verified": 4, "closed": 5}

SYSTEM_PROMPTS = {
    "agent": "You are a project copilot. Give concise, executable guidance.",
    "lab": (
        "You are a laboratory safety assistant. Output in this order: conclusion, steps, forbidden actions, escalation. "
        "Never provide unsafe or policy-violating instructions."
    ),
}

PPE_HINTS = {
    "Splash goggles": ["acid", "base", "solvent", "splash", "corrosive", "etchant", "酸", "碱", "溶剂", "飞溅", "腐蚀"],
    "Face shield": ["splash", "high pressure", "flying debris", "pressurized", "飞溅", "高压", "碎片"],
    "Chemical resistant gloves": [
        "acid",
        "base",
        "solvent",
        "corrosive",
        "hazardous chemical",
        "酸",
        "碱",
        "溶剂",
        "腐蚀",
        "危化品",
    ],
    "Lab coat": ["chemical", "biosafety", "reagent", "sample", "hazard", "化学", "生物", "试剂", "样本", "危险"],
    "Respiratory protection": ["toxic gas", "vapor", "inhalation", "fume", "powder", "有毒气体", "蒸气", "吸入", "烟雾", "粉尘"],
    "Cryogenic gloves": ["liquid nitrogen", "cryogenic", "low temperature", "dewars", "液氮", "深冷", "低温", "杜瓦"],
    "Electrical gloves": ["electric", "shock", "high voltage", "live circuit", "触电", "带电", "高压", "电路"],
}

HAZARD_HINTS = {
    "Chemical": ["acid", "base", "solvent", "corrosive", "hazardous chemical", "oxidizer", "flammable", "酸", "碱", "溶剂", "腐蚀", "危化品", "氧化剂", "易燃"],
    "Biosafety": ["bio", "pathogen", "sample", "sterilization", "culture", "blood", "生物", "病原", "样本", "灭菌", "培养", "血液"],
    "Electrical": ["electric", "shock", "high voltage", "power", "circuit", "battery", "触电", "带电", "高压", "电源", "电路", "电池"],
    "Fire": ["fire", "smoke", "ignition", "burn", "flammable", "reflux", "火", "起火", "冒烟", "点火源", "燃烧", "回流", "易燃"],
    "Cryogenic": ["liquid nitrogen", "cryogenic", "frostbite", "dewars", "液氮", "深冷", "冻伤", "杜瓦"],
    "Mechanical": ["centrifuge", "rotation", "pinch", "moving parts", "press", "离心机", "旋转", "夹伤", "运动部件", "压力机"],
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
_INCIDENT_LOCK = threading.Lock()









def safe_read_csv_rows(path: Path) -> list[dict[str, str]]:
    """读取 CSV 为字典列表；文件不存在时返回空列表（不抛异常）。"""
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [row for row in csv.DictReader(f)]






def load_kb_entries() -> list[dict[str, str]]:
    if not KB_FILE.exists():
        return []
    rows: list[dict[str, str]] = []
    with KB_FILE.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            title = (row.get("title") or "").strip()
            question = (row.get("question") or "").strip()
            answer = (row.get("answer") or "").strip()
            steps = (row.get("steps") or "").strip()
            forbidden = (row.get("forbidden") or "").strip()
            emergency = (row.get("emergency") or "").strip()
            ppe = (row.get("ppe") or "").strip()
            hazard_types = (row.get("hazard_types") or "").strip()
            tags = (row.get("tags") or "").strip()
            blob = normalize_search_text(
                " ".join(
                    [
                        title,
                        question,
                        answer,
                        steps,
                        forbidden,
                        emergency,
                        ppe,
                        hazard_types,
                        tags,
                    ]
                )
            )
            rows.append(
                {
                    "id": (row.get("id") or "").strip(),
                    "title": title,
                    "question": question,
                    "source_title": (row.get("source_title") or "").strip(),
                    "source_org": (row.get("source_org") or "").strip(),
                    "source_url": (row.get("source_url") or "").strip(),
                    "risk_level": (row.get("risk_level") or "").strip(),
                    "category": (row.get("category") or "").strip(),
                    "subcategory": (row.get("subcategory") or "").strip(),
                    "hazard_types": hazard_types,
                    "answer": answer,
                    "steps": steps,
                    "forbidden": forbidden,
                    "emergency": emergency,
                    "ppe": ppe,
                    "tags": tags,
                    "title_blob": normalize_search_text(" ".join([title, question])),
                    "tag_blob": normalize_search_text(" ".join([hazard_types, tags])),
                    "body_blob": normalize_search_text(" ".join([answer, steps, forbidden, emergency, ppe])),
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

