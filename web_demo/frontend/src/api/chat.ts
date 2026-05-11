// ============================================
// 问答 API
// ============================================

import { get, post } from "./client";
import type { ChatRequest, ChatResponse, SearchResponse } from "../types";
import { isDemoModeEnabled } from "../mock/demoMode";
import { getMockSearch, postMockChat } from "../mock/mockApi";

export async function chat(request: ChatRequest): Promise<ChatResponse> {
  if (isDemoModeEnabled()) {
    return postMockChat(request);
  }
  return post<ChatResponse>("/chat", request);
}

export async function search(query: string, topK = 5): Promise<SearchResponse> {
  if (isDemoModeEnabled()) {
    return getMockSearch(query);
  }
  return get<SearchResponse>(`/search?q=${encodeURIComponent(query)}&top_k=${topK}`);
}
