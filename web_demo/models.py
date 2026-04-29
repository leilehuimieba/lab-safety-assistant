from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field

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
    review_status: str = Field(default="pending", description="pending / approved / rejected")
    reviewed_by: str = ""
    reviewed_at: str = ""
    review_comment: str = ""


class ChecklistReviewRequest(BaseModel):
    action: str = Field(pattern="^(approve|reject)$")
    reviewer: str = Field(default="teacher", max_length=120)
    comment: str = Field(default="", max_length=1000)


class ChecklistReviewResponse(BaseModel):
    record_id: str
    review_status: str
    reviewed_by: str
    reviewed_at: str
    review_comment: str
    message: str


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


class TrainingRosterItem(BaseModel):
    student_id: str = ""
    name: str
    class_name: str = ""
    lab_group: str = ""
    completed: bool = False
    passed: bool = False
    latest_score: int = 0
    latest_submitted_at: str = ""


class TrainingRosterStatusResponse(BaseModel):
    total_required: int
    completed_count: int
    passed_count: int
    incomplete_count: int
    incomplete_students: list[TrainingRosterItem] = Field(default_factory=list)
    roster: list[TrainingRosterItem] = Field(default_factory=list)


class TrainingRosterUploadRequest(BaseModel):
    csv_text: str = Field(min_length=1)


class TrainingRosterUploadResponse(BaseModel):
    message: str
    saved_count: int
    status: TrainingRosterStatusResponse


class DashboardMetric(BaseModel):
    label: str
    value: str
    detail: str = ""


class DashboardLowConfidenceItem(BaseModel):
    label: str
    count: int


class DashboardHighRiskScenario(BaseModel):
    submitted_at: str
    scenario: str
    risk_level: str
    allow_start: bool
    operator: str = ""


class AdminDashboardResponse(BaseModel):
    metrics: list[DashboardMetric] = Field(default_factory=list)
    low_confidence_top: list[DashboardLowConfidenceItem] = Field(default_factory=list)
    recent_high_risk_scenarios: list[DashboardHighRiskScenario] = Field(default_factory=list)
    incident_summary: dict[str, int] = Field(default_factory=dict)
    overdue_incidents: list[str] = Field(default_factory=list)


class DemoMetaResponse(BaseModel):
    app_version: str
    chat_lane_lab: str
    chat_lane_agent: str
    acceptance_status: str
    formal_eval_score: str
    stability_status: str
    knowledge_base_rows: int
    knowledge_base_imported: int
    demo_port: str
    runtime_model: str


class WorkspaceStatusItem(BaseModel):
    label: str
    count: int


class WorkspaceStatusResponse(BaseModel):
    dify_enabled: bool
    dify_base_url: str
    dify_timeout: float
    dify_app_key_configured: bool
    dify_connection_status: str
    kb_rows: int
    kb_imported: int
    low_confidence_queue_count: int
    top_categories: list[WorkspaceStatusItem] = Field(default_factory=list)
    top_hazards: list[WorkspaceStatusItem] = Field(default_factory=list)


class IncidentCreateRequest(BaseModel):
    reporter: str = Field(default="anonymous", max_length=120)
    title: str = Field(min_length=1, max_length=200)
    scenario: str = Field(min_length=1, max_length=3000)
    severity: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    location: str = Field(default="", max_length=200)
    cause_categories: list[str] = Field(default_factory=list)
    immediate_actions: list[str] = Field(default_factory=list)
    corrective_actions: list[str] = Field(default_factory=list)
    owner: str = Field(default="", max_length=120)
    due_date: str = Field(default="", max_length=40)


class IncidentUpdateRequest(BaseModel):
    status: str = Field(default="in_review", pattern="^(open|in_review|action_in_progress|verified|closed)$")
    corrective_actions: list[str] = Field(default_factory=list)
    owner: str = Field(default="", max_length=120)
    due_date: str = Field(default="", max_length=40)
    closure_notes: str = Field(default="", max_length=1000)


class IncidentRecord(BaseModel):
    incident_id: str
    reported_at: str
    updated_at: str
    reporter: str
    title: str
    scenario: str
    severity: str
    status: str
    location: str = ""
    cause_categories: list[str] = Field(default_factory=list)
    immediate_actions: list[str] = Field(default_factory=list)
    corrective_actions: list[str] = Field(default_factory=list)
    owner: str = ""
    due_date: str = ""
    closure_notes: str = ""
    recurrence_risk: str = "medium"
    overdue: bool = False
    overdue_days: int = 0


