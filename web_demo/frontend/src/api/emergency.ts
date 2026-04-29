// ============================================
// 应急卡片 API
// ============================================

import { get, post } from "./client";
import type { EmergencyCard, EmergencyMatchResponse } from "../types";

export async function getEmergencyCards(): Promise<EmergencyCard[]> {
  return get<EmergencyCard[]>("/emergency/cards");
}

export async function matchEmergencyCard(query: string): Promise<EmergencyMatchResponse> {
  return post<EmergencyMatchResponse>("/emergency/match", { query });
}
