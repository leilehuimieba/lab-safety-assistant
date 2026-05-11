// ============================================
// 事故管理 API
// ============================================

import { get, post, patch, del } from "./client";
import type {
  IncidentListResponse,
  CreateIncidentRequest,
  UpdateIncidentRequest,
  IncidentRecord,
} from "../types";
import { isDemoModeEnabled } from "../mock/demoMode";
import {
  deleteMockIncident,
  getMockIncidents,
  patchMockIncident,
  postMockCreateIncident,
} from "../mock/mockApi";

export async function getIncidents(): Promise<IncidentListResponse> {
  if (isDemoModeEnabled()) {
    return getMockIncidents();
  }
  return get<IncidentListResponse>("/incidents");
}

export async function createIncident(data: CreateIncidentRequest): Promise<IncidentRecord> {
  if (isDemoModeEnabled()) {
    return postMockCreateIncident(data);
  }
  return post<IncidentRecord>("/incidents", data);
}

export async function updateIncident(
  id: string,
  data: UpdateIncidentRequest
): Promise<IncidentRecord> {
  if (isDemoModeEnabled()) {
    return patchMockIncident(id, data);
  }
  return patch<IncidentRecord>(`/incidents/${encodeURIComponent(id)}`, data);
}

export async function deleteIncident(id: string): Promise<void> {
  if (isDemoModeEnabled()) {
    return deleteMockIncident();
  }
  return del<void>(`/incidents/${encodeURIComponent(id)}`);
}
