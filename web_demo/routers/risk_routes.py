from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..models import (
    ChecklistGenerateRequest, ChecklistReviewRequest, ChecklistReviewResponse,
    ChecklistSubmitRequest, ChecklistSubmitResponse,
    ChecklistTemplateResponse, RiskAssessRequest, RiskAssessResponse,
)
from ..services import (
    build_checklist_template, build_risk_assessment,
    evaluate_checklist_submission, match_rule,
    retrieve_citations, review_checklist_submission,
)

router = APIRouter()


@router.post("/api/risk_assess", response_model=RiskAssessResponse)
def risk_assess(payload: RiskAssessRequest) -> RiskAssessResponse:
    scenario = payload.scenario.strip()
    if not scenario:
        raise HTTPException(status_code=400, detail="scenario is required.")
    citations = retrieve_citations(scenario, top_k=5)
    return build_risk_assessment(scenario, citations, match_rule(scenario))


@router.post("/api/risk/assess", response_model=RiskAssessResponse)
def risk_assess_alias(payload: RiskAssessRequest) -> RiskAssessResponse:
    return risk_assess(payload)


@router.post("/api/checklist/template", response_model=ChecklistTemplateResponse)
def checklist_template(payload: ChecklistGenerateRequest) -> ChecklistTemplateResponse:
    return build_checklist_template(payload.scenario.strip())


@router.post("/api/checklist/submit", response_model=ChecklistSubmitResponse)
def checklist_submit(payload: ChecklistSubmitRequest) -> ChecklistSubmitResponse:
    if not payload.checklist:
        raise HTTPException(status_code=400, detail="checklist is required.")
    return evaluate_checklist_submission(payload)


@router.patch("/api/checklist/{record_id}/review", response_model=ChecklistReviewResponse)
def checklist_review(record_id: str, payload: ChecklistReviewRequest) -> ChecklistReviewResponse:
    return review_checklist_submission(record_id, payload)
