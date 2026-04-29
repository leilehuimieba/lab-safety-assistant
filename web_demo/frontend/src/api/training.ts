// ============================================
// 培训 API
// ============================================

import { get, post } from "./client";
import type {
  TrainingSessionResponse,
  TrainingSubmitRequest,
  TrainingSubmitResponse,
  TrainingStatsResponse,
  TrainingRosterStatusResponse,
} from "../types";

export async function getTrainingQuestions(limit?: number): Promise<TrainingSessionResponse> {
  const qs = limit !== undefined ? `?limit=${limit}` : "";
  return get<TrainingSessionResponse>(`/training/questions${qs}`);
}

export async function submitTrainingAnswers(
  sessionId: string,
  participant: string,
  answers: TrainingSubmitRequest["answers"]
): Promise<TrainingSubmitResponse> {
  const request: TrainingSubmitRequest = { session_id: sessionId, participant, answers };
  return post<TrainingSubmitResponse>("/training/submit", request);
}

export async function getTrainingStats(): Promise<TrainingStatsResponse> {
  return get<TrainingStatsResponse>("/training/stats");
}

export async function getTrainingRosterStatus(): Promise<TrainingRosterStatusResponse> {
  return get<TrainingRosterStatusResponse>("/training/roster");
}

export async function uploadTrainingRoster(file: File): Promise<TrainingRosterStatusResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return post<TrainingRosterStatusResponse>("/training/roster", formData);
}
