// ============================================
// 管理看板 API
// ============================================

import { get } from "./client";
import type { AdminDashboardResponse, WeeklyReportResponse } from "../types";

export async function getAdminDashboard(
  days?: number,
  riskLevel?: string,
  incidentStatus?: string
): Promise<AdminDashboardResponse> {
  const params = new URLSearchParams();
  if (days !== undefined) params.set("days", String(days));
  if (riskLevel !== undefined) params.set("risk_level", riskLevel);
  if (incidentStatus !== undefined) params.set("incident_status", incidentStatus);
  const qs = params.toString();
  return get<AdminDashboardResponse>(qs ? `/admin/dashboard?${qs}` : "/admin/dashboard");
}

export async function exportData(scope?: string, days?: number): Promise<Blob> {
  const params = new URLSearchParams();
  if (scope !== undefined) params.set("scope", scope);
  if (days !== undefined) params.set("days", String(days));
  const qs = params.toString();
  return get<Blob>(qs ? `/admin/export?${qs}` : "/admin/export", { responseType: "blob" });
}

export async function getWeeklyReport(): Promise<WeeklyReportResponse> {
  return get<WeeklyReportResponse>("/admin/weekly-report");
}
