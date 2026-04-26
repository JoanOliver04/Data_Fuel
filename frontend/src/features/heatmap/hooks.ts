import { useQuery } from "@tanstack/react-query";

import { fetchHeatmap } from "./api";
import type { HeatmapParams } from "./types";

/** 5-minute cache aligned with the backend MITECO refresh interval. */
const STALE_MS = 5 * 60_000;

export function useHeatmap(params: HeatmapParams | null) {
  return useQuery({
    queryKey: ["heatmap", params],
    queryFn: () => fetchHeatmap(params!),
    enabled: params !== null,
    staleTime: STALE_MS,
    gcTime: STALE_MS,
  });
}
