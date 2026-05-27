import { apiFetch } from "@/lib/api-client";

import type {
  ExplainRecommendationRequest,
  ExplainRecommendationResponse,
  GlobalFeatureImportance,
} from "./types";

export function fetchXaiExplanation(
  params: ExplainRecommendationRequest,
): Promise<ExplainRecommendationResponse> {
  return apiFetch<ExplainRecommendationResponse>("/api/v1/xai/explain-recommendation", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export function fetchGlobalFeatureImportance(): Promise<GlobalFeatureImportance> {
  return apiFetch<GlobalFeatureImportance>("/api/v1/xai/global-feature-importance");
}
