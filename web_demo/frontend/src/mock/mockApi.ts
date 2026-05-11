import type {
  AdminDashboardResponse,
  ChatRequest,
  ChatResponse,
  ChecklistSubmitRequest,
  ChecklistSubmitResponse,
  ChecklistTemplateRequest,
  ChecklistTemplateResponse,
  CreateIncidentRequest,
  DemoMetaResponse,
  EmergencyCard,
  EmergencyMatchResponse,
  IncidentListResponse,
  IncidentRecord,
  RiskAssessRequest,
  RiskAssessResponse,
  SearchResponse,
  TrainingRosterStatusResponse,
  TrainingSessionResponse,
  TrainingStatsResponse,
  TrainingSubmitRequest,
  TrainingSubmitResponse,
  UpdateIncidentRequest,
  WeeklyReportResponse,
  WorkspaceStatusResponse,
} from "../types";
import {
  demoMeta,
  demoWorkspaceStatus,
  mockAdminDashboard,
  mockChat,
  mockChecklistSubmit,
  mockChecklistTemplate,
  mockCreateIncident,
  mockEmergencyCards,
  mockEmergencyMatch,
  mockIncidents,
  mockRiskAssess,
  mockSearch,
  mockTrainingRoster,
  mockTrainingSession,
  mockTrainingStats,
  mockTrainingSubmit,
  mockUpdateIncident,
  mockWeeklyReport,
} from "./data";

function delay<T>(data: T, ms = 250): Promise<T> {
  return new Promise((resolve) => {
    window.setTimeout(() => resolve(data), ms);
  });
}

export function getMockWorkspaceStatus(): Promise<WorkspaceStatusResponse> {
  return delay(structuredClone(demoWorkspaceStatus));
}

export function getMockMeta(): Promise<DemoMetaResponse> {
  return delay(structuredClone(demoMeta));
}

export function postMockChat(request: ChatRequest): Promise<ChatResponse> {
  return delay(mockChat(request), 450);
}

export function getMockSearch(query: string): Promise<SearchResponse> {
  return delay(mockSearch(query), 200);
}

export function postMockRiskAssess(
  request: RiskAssessRequest
): Promise<RiskAssessResponse> {
  return delay(mockRiskAssess(request), 500);
}

export function postMockChecklistTemplate(
  request: ChecklistTemplateRequest
): Promise<ChecklistTemplateResponse> {
  return delay(mockChecklistTemplate(request), 700);
}

export function postMockChecklistSubmit(
  request: ChecklistSubmitRequest
): Promise<ChecklistSubmitResponse> {
  return delay(mockChecklistSubmit(request), 450);
}

export function getMockEmergencyCards(): Promise<EmergencyCard[]> {
  return delay(mockEmergencyCards(), 350);
}

export function postMockEmergencyMatch(
  query: string
): Promise<EmergencyMatchResponse> {
  return delay(mockEmergencyMatch(query), 300);
}

export function getMockTrainingQuestions(): Promise<TrainingSessionResponse> {
  return delay(mockTrainingSession(), 450);
}

export function postMockTrainingSubmit(
  request: TrainingSubmitRequest
): Promise<TrainingSubmitResponse> {
  return delay(mockTrainingSubmit(request), 400);
}

export function getMockTrainingStats(): Promise<TrainingStatsResponse> {
  return delay(mockTrainingStats(), 250);
}

export function getMockTrainingRoster(): Promise<TrainingRosterStatusResponse> {
  return delay(mockTrainingRoster(), 250);
}

export function getMockAdminDashboard(): Promise<AdminDashboardResponse> {
  return delay(mockAdminDashboard(), 380);
}

export function getMockWeeklyReport(): Promise<WeeklyReportResponse> {
  return delay(mockWeeklyReport(), 200);
}

export function getMockExportCsv(): Promise<Blob> {
  const csv = `scenario,risk_level,allow_start,operator\n浓硫酸参与的有机合成预热实验,High,false,张三\n离心前生物样本裂解操作,High,false,王五\n高压气瓶更换与气路检测,Critical,false,赵六\n`;
  return delay(new Blob([csv], { type: "text/csv;charset=utf-8" }), 250);
}

export function getMockIncidents(): Promise<IncidentListResponse> {
  return delay(mockIncidents(), 350);
}

export function postMockCreateIncident(
  request: CreateIncidentRequest
): Promise<IncidentRecord> {
  return delay(mockCreateIncident(request), 320);
}

export function patchMockIncident(
  id: string,
  request: UpdateIncidentRequest
): Promise<IncidentRecord> {
  return delay(mockUpdateIncident(id, request), 250);
}

export function deleteMockIncident(): Promise<void> {
  return delay(undefined, 150);
}
