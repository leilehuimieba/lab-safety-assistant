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
import { isDemoModeEnabled } from "../mock/demoMode";
import {
  postMockChecklistSubmit,
  postMockChecklistTemplate,
  postMockRiskAssess,
} from "../mock/mockApi";

export async function assessRisk(request: RiskAssessRequest): Promise<RiskAssessResponse> {
  if (isDemoModeEnabled()) {
    return postMockRiskAssess(request);
  }
  return post<RiskAssessResponse>("/risk/assess", request);
}

export async function getChecklistTemplate(
  request: ChecklistTemplateRequest
): Promise<ChecklistTemplateResponse> {
  if (isDemoModeEnabled()) {
    return postMockChecklistTemplate(request);
  }
  return post<ChecklistTemplateResponse>("/checklist/template", request);
}

export async function submitChecklist(
  request: ChecklistSubmitRequest
): Promise<ChecklistSubmitResponse> {
  if (isDemoModeEnabled()) {
    return postMockChecklistSubmit(request);
  }
  return post<ChecklistSubmitResponse>("/checklist/submit", request);
}
