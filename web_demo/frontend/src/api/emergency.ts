// ============================================
// 应急卡片 API
// ============================================

import { get, post } from "./client";
import type { EmergencyCard, EmergencyMatchResponse } from "../types";
import { isDemoModeEnabled } from "../mock/demoMode";
import { getMockEmergencyCards, postMockEmergencyMatch } from "../mock/mockApi";

export async function getEmergencyCards(): Promise<EmergencyCard[]> {
  if (isDemoModeEnabled()) {
    return getMockEmergencyCards();
  }
  return get<EmergencyCard[]>("/emergency/cards");
}

export async function matchEmergencyCard(query: string): Promise<EmergencyMatchResponse> {
  if (isDemoModeEnabled()) {
    return postMockEmergencyMatch(query);
  }
  return post<EmergencyMatchResponse>("/emergency/match", { query });
}
