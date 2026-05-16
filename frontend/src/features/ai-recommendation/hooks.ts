import { useMutation } from "@tanstack/react-query";

import { fetchAiRecommendation } from "./api";

export function useAiRecommendation() {
  return useMutation({
    mutationFn: fetchAiRecommendation,
  });
}
