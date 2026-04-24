import { useQuery } from "@tanstack/react-query";

import { fetchSmartAdvice } from "./api";
import type { SmartAdviceParams } from "./types";

export function useSmartAdvice(params: SmartAdviceParams | null) {
  return useQuery({
    queryKey: ["smart-advice", params],
    queryFn: () => fetchSmartAdvice(params!),
    enabled: params !== null,
    staleTime: 5 * 60_000,
    retry: false,
  });
}
