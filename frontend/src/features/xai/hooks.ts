import { useQuery } from "@tanstack/react-query";

import { fetchGlobalFeatureImportance, fetchXaiExplanation } from "./api";
import type { ExplainRecommendationRequest } from "./types";

/**
 * Local SHAP explanation for one recommendation. Disabled until `params` is
 * non-null, so the request only fires once the user has triggered a
 * recommendation. The explanation embeds the global importances too, so the
 * card needs no second call.
 */
export function useXaiExplanation(params: ExplainRecommendationRequest | null) {
  return useQuery({
    queryKey: ["xai-explanation", params],
    queryFn: () => fetchXaiExplanation(params as ExplainRecommendationRequest),
    enabled: params !== null,
    staleTime: 5 * 60_000,
    retry: false,
  });
}

/** Standalone global feature importance (model-wide), cached for an hour. */
export function useGlobalFeatureImportance(enabled = true) {
  return useQuery({
    queryKey: ["xai-global-importance"],
    queryFn: fetchGlobalFeatureImportance,
    enabled,
    staleTime: 60 * 60_000,
  });
}
