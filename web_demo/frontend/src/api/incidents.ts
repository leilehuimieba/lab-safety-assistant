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

export async function getIncidents(): Promise<IncidentListResponse> {
  return get<IncidentListResponse>("/incidents");
}

export async function createIncident(data: CreateIncidentRequest): Promise<IncidentRecord> {
  return post<IncidentRecord>("/incidents", data);
}

export async function updateIncident(
  id: string,
  data: UpdateIncidentRequest
): Promise<IncidentRecord> {
  return patch<IncidentRecord>(`/incidents/${encodeURIComponent(id)}`, data);
}

export async function deleteIncident(id: string): Promise<void> {
  return del<void>(`/incidents/${encodeURIComponent(id)}`);
}
