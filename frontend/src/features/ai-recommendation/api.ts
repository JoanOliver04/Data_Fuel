import { apiFetch } from "@/lib/api-client";

import type { AiRecommendationRequest, AiRecommendationResponse } from "./types";

export function fetchAiRecommendation(
  params: AiRecommendationRequest,
): Promise<AiRecommendationResponse> {
  return apiFetch<AiRecommendationResponse>("/api/v1/predictions/recommendation", {
    method: "POST",
    body: JSON.stringify(params),
  });
}
