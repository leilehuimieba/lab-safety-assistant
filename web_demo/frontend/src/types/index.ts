// ============================================
// 实验室安全小助手 — 全局 TypeScript 类型定义
// 与后端 Pydantic 模型严格对应
// ============================================

// === 通用 ===
export interface Citation {
  kb_id: string;
  title: string;
  source_title: string;
  source_org: string;
  source_url: string;
  risk_level: string;
  snippet: string;
  score: number;
}

// === 问答 ===
export interface ChatRequest {
  mode: "lab" | "agent";
  question: string;
}

export type ChatDecision =
  | "llm_answer"
  | "llm_answer_guarded"
  | "rule_blocked"
  | "emergency_redirect"
  | "need_more_info"
  | "llm_low_confidence"
  | "llm_fallback_structured";

export interface ChatResponse {
  answer: string;
  mode: string;
  model: string;
  decision: ChatDecision;
  risk_level: string;
  matched_rule_id: string;
  matched_rule_action: string;
  low_confidence: boolean;
  low_confidence_reason: string;
  followup_logged: boolean;
  citations: Citation[];
}

export interface SearchResponse {
  results: Citation[];
}

// === 风险评估 ===
export interface RiskAssessRequest {
  scenario: string;
}

export type RiskLevel = "Low" | "Medium-Low" | "Medium" | "High" | "Critical";

export interface RiskAssessResponse {
  scenario: string;
  risk_score: number;
  risk_level: RiskLevel;
  key_hazards: string[];
  ppe: string[];
  forbidden: string[];
  emergency_actions: string[];
  recommended_steps: string[];
  low_confidence: boolean;
  low_confidence_reason: string;
  citations: Citation[];
}

// === 开工检查 ===
export interface ChecklistItem {
  id: string;
  label: string;
  critical: boolean;
  checked: boolean;
  note: string;
}

export interface ChecklistTemplateRequest {
  scenario: string;
  chemicals: string;
  equipment: string;
  procedure: string;
}

export interface ChecklistTemplateResponse {
  scenario: string;
  risk_score: number;
  risk_level: string;
  key_hazards: string[];
  checklist: ChecklistItem[];
  recommended_actions: string[];
  citations: Citation[];
}

export interface ChecklistSubmitRequest {
  scenario: string;
  operator: string;
  checklist: ChecklistItem[];
}

export interface ChecklistSubmitResponse {
  record_id: string;
  submitted_at: string;
  scenario: string;
  operator: string;
  risk_score: number;
  risk_level: string;
  key_hazards: string[];
  allow_start: boolean;
  blocking_reasons: string[];
  next_actions: string[];
}

// === 应急卡片 ===
export interface EmergencyCard {
  id: string;
  title: string;
  category: string;
  summary: string;
  trigger_signs: string[];
  immediate_actions: string[];
  forbidden: string[];
  ppe: string[];
  escalation: string[];
}

export interface EmergencyMatchResponse {
  query: string;
  matched_card_id: string;
  confidence: number;
  card: EmergencyCard | null;
}

// === 培训 ===
export interface TrainingQuestion {
  id: string;
  category: string;
  prompt: string;
  options: string[];
  multiple: boolean;
  references: string[];
}

export interface TrainingSessionResponse {
  session_id: string;
  total_questions: number;
  pass_threshold: number;
  questions: TrainingQuestion[];
}

export interface TrainingAnswer {
  question_id: string;
  selected_indices: number[];
}

export interface TrainingSubmitRequest {
  session_id: string;
  participant: string;
  answers: TrainingAnswer[];
}

export interface TrainingReviewItem {
  question_id: string;
  category: string;
  prompt: string;
  selected_indices: number[];
  correct_indices: number[];
  correct: boolean;
  explanation: string;
  references: string[];
}

export interface TrainingSubmitResponse {
  attempt_id: string;
  session_id: string;
  participant: string;
  submitted_at: string;
  score: number;
  total_questions: number;
  pass_threshold: number;
  passed: boolean;
  weak_categories: string[];
  recommended_actions: string[];
  review: TrainingReviewItem[];
}

export interface TrainingStatsResponse {
  attempt_count: number;
  pass_rate: number;
  average_score: number;
  latest_submitted_at: string;
  category_mistakes: Record<string, number>;
  recent_scores: number[];
}

export interface TrainingRosterItem {
  student_id: string;
  name: string;
  class_name: string;
  lab_group: string;
  completed: boolean;
  passed: boolean;
  latest_score: number;
  latest_submitted_at: string;
}

export interface TrainingRosterStatusResponse {
  roster: TrainingRosterItem[];
}

// === 管理看板 ===
export interface DashboardMetric {
  label: string;
  value: string;
  detail: string;
}

export interface HighRiskScenario {
  submitted_at: string;
  scenario: string;
  risk_level: string;
  allow_start: boolean;
  operator: string;
}

export interface AdminDashboardResponse {
  metrics: DashboardMetric[];
  low_confidence_top: { label: string; count: number }[];
  recent_high_risk_scenarios: HighRiskScenario[];
  incident_summary: Record<string, number>;
  overdue_incidents: string[];
}

export interface WeeklyReportResponse {
  report: string;
}

// === 事故 ===
export type IncidentSeverity = "low" | "medium" | "high" | "critical";
export type IncidentStatus = "open" | "in_review" | "action_in_progress" | "verified" | "closed";

export interface IncidentRecord {
  incident_id: string;
  reported_at: string;
  updated_at: string;
  reporter: string;
  title: string;
  scenario: string;
  severity: IncidentSeverity;
  status: IncidentStatus;
  location: string;
  cause_categories: string[];
  immediate_actions: string[];
  corrective_actions: string[];
  owner: string;
  due_date: string;
  closure_notes: string;
  recurrence_risk: string;
  overdue: boolean;
  overdue_days: number;
}

export interface CreateIncidentRequest {
  title: string;
  scenario: string;
  severity: IncidentSeverity;
  location: string;
  reporter: string;
  cause_categories: string[];
  immediate_actions: string[];
  owner: string;
  due_date: string;
}

export interface UpdateIncidentRequest {
  status?: IncidentStatus;
  severity?: IncidentSeverity;
  owner?: string;
  corrective_actions?: string[];
  closure_notes?: string;
  due_date?: string;
}

export interface IncidentListResponse {
  incidents: IncidentRecord[];
  total: number;
}

// === 工作区状态 ===
export interface WorkspaceStatusResponse {
  dify_enabled: boolean;
  dify_connection_status: string;
  kb_rows: number;
  kb_imported: number;
  low_confidence_queue_count: number;
  top_categories: { label: string; count: number }[];
  top_hazards: { label: string; count: number }[];
}

export interface MetaInfoResponse {
  version: string;
  name: string;
  description: string;
}

// === 健康检查 ===
export interface HealthResponse {
  status: string;
}

// === 决策卡片状态 ===
export type DecisionType = "allow" | "review" | "block";

export interface DecisionCardData {
  type: DecisionType;
  title: string;
  subtitle?: string;
  reasons?: string[];
  actions?: string[];
  citations?: Citation[];
  details?: Record<string, string>;
}

// === 路由页面 ===
export type PageRoute =
  | "/"
  | "/checklist"
  | "/emergency"
  | "/training"
  | "/teacher"
  | "/admin"
  | "/incidents"
  | "/status";

export interface NavItem {
  route: PageRoute;
  label: string;
  icon: string;
  group: "student" | "teacher" | "admin";
}

// === API 错误 ===
export interface ApiError {
  detail: string;
  status: number;
}
