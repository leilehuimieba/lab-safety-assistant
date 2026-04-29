// ============================================
// 问答 API
// ============================================

import { get, post } from "./client";
import type { ChatRequest, ChatResponse, SearchResponse } from "../types";

export async function chat(request: ChatRequest): Promise<ChatResponse> {
  return post<ChatResponse>("/chat", request);
}

export async function search(query: string, topK = 5): Promise<SearchResponse> {
  return get<SearchResponse>(`/search?q=${encodeURIComponent(query)}&top_k=${topK}`);
}
