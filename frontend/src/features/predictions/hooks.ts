import { useQuery } from "@tanstack/react-query";

import { fetchPrediction } from "./api";

export function usePrediction(stationId: number, fuelType: string) {
  return useQuery({
    queryKey: ["prediction", stationId, fuelType],
    queryFn: () => fetchPrediction(stationId, fuelType),
    staleTime: 30 * 60_000,
  });
}
