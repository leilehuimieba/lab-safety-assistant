from __future__ import annotations

"""风险评估与检查清单服务

- build_risk_assessment: 基于规则严重性、引用风险等级和关键词计算风险评分
- build_checklist_template: 根据风险等级和危险类型生成个性化检查清单
- evaluate_checklist_submission: 评估检查清单提交结果并记录运行数据
- filter_checklist_rows / dedupe_checklist_items: 检查清单数据筛选与去重工具
"""
import csv
import json
import os
from datetime import datetime
from typing import Any
from uuid import uuid4

from fastapi import HTTPException

from ..models import (
    ChecklistItem, ChecklistReviewRequest, ChecklistReviewResponse,
    ChecklistSubmitRequest, ChecklistSubmitResponse,
    ChecklistTemplateResponse, RiskAssessResponse,
)
from ..repositories import (
    BASE_CHECKLIST_ITEMS, CHECKLIST_HEADERS, CHECKLIST_RUNS_FILE,
    HAZARD_CHECKLIST_ITEMS, HIGH_RISK_CHECKLIST_ITEMS,
    HAZARD_HINTS, PPE_HINTS, RISK_LABEL, SEVERITY_SCORE,
    normalize_search_text, write_csv_row,
)
from .kb_service import match_rule, retrieve_citations
from .answer_service import assess_low_confidence
from libs.time_utils import within_days

def build_risk_assessment(scenario: str, citations: list[Citation], rule: dict[str, Any] | None) -> RiskAssessResponse:
    severity_score = SEVERITY_SCORE.get(str((rule or {}).get("severity", "")).lower(), 1)
    citation_score = max(
        [int(float(item.risk_level)) for item in citations if str(item.risk_level).replace(".", "", 1).isdigit()] or [1]
    )
    text_norm = normalize_search_text(scenario)
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
    # 有阻断项 → 待审核；全部通过 → 自动通过
    initial_review_status = "pending" if blocking else "approved"
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
            "review_status": initial_review_status,
            "reviewed_by": "",
            "reviewed_at": "",
            "review_comment": "",
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
        review_status=initial_review_status,
    )
def filter_checklist_rows(rows: list[dict[str, str]], *, days: int, risk_level: str) -> list[dict[str, str]]:
    target_risk = (risk_level or "").strip().lower()
    filtered: list[dict[str, str]] = []
    for row in rows:
        if days > 0 and not within_days(row.get("submitted_at", ""), days):
            continue
        if target_risk and (row.get("risk_level") or "").strip().lower() != target_risk:
            continue
        filtered.append(row)
    return filtered

def review_checklist_submission(record_id: str, payload: ChecklistReviewRequest) -> ChecklistReviewResponse:
    if not CHECKLIST_RUNS_FILE.exists():
        raise HTTPException(status_code=404, detail="no checklist records found.")

    rows: list[dict[str, str]] = []
    target_found = False
    reviewed_at = datetime.now().isoformat(timespec="seconds")
    with CHECKLIST_RUNS_FILE.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            # 补齐旧记录的缺失 review 字段
            for header in CHECKLIST_HEADERS:
                if header not in row:
                    row[header] = ""
            if (row.get("record_id") or "").strip() == record_id:
                target_found = True
                row["review_status"] = "approved" if payload.action == "approve" else "rejected"
                row["reviewed_by"] = payload.reviewer.strip() or "teacher"
                row["reviewed_at"] = reviewed_at
                row["review_comment"] = payload.comment.strip()
            rows.append(row)

    if not target_found:
        raise HTTPException(status_code=404, detail=f"checklist record {record_id} not found.")

    CHECKLIST_RUNS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with CHECKLIST_RUNS_FILE.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CHECKLIST_HEADERS)
        writer.writeheader()
        writer.writerows(rows)

    action_name = "已批准" if payload.action == "approve" else "已驳回"
    return ChecklistReviewResponse(
        record_id=record_id,
        review_status=("approved" if payload.action == "approve" else "rejected"),
        reviewed_by=payload.reviewer.strip() or "teacher",
        reviewed_at=reviewed_at,
        review_comment=payload.comment.strip(),
        message=f"{action_name}。操作人: {payload.reviewer}",
    )
