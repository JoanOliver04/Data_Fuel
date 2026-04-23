import { useQuery } from "@tanstack/react-query";

import { fetchRecommendations } from "./api";
import type { RecommendationParams } from "./types";

export function useRecommendations(params: RecommendationParams | null) {
  return useQuery({
    queryKey: ["recommendations", params],
    queryFn: () => fetchRecommendations(params!),
    enabled: params !== null,
    staleTime: 5 * 60_000,
  });
}
