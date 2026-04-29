// ============================================
// 风险评估 + 开工检查 API
// ============================================

import { post } from "./client";
import type {
  RiskAssessRequest,
  RiskAssessResponse,
  ChecklistTemplateRequest,
  ChecklistTemplateResponse,
  ChecklistSubmitRequest,
  ChecklistSubmitResponse,
} from "../types";

export async function assessRisk(request: RiskAssessRequest): Promise<RiskAssessResponse> {
  return post<RiskAssessResponse>("/risk/assess", request);
}

export async function getChecklistTemplate(
  request: ChecklistTemplateRequest
): Promise<ChecklistTemplateResponse> {
  return post<ChecklistTemplateResponse>("/checklist/template", request);
}

export async function submitChecklist(
  request: ChecklistSubmitRequest
): Promise<ChecklistSubmitResponse> {
  return post<ChecklistSubmitResponse>("/checklist/submit", request);
}
