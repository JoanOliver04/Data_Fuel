import { useQuery } from "@tanstack/react-query";

import { fetchPriceHistory } from "./api";

export function usePriceHistory(stationId: number, fuelType: string, enabled = false) {
  return useQuery({
    queryKey: ["price-history", stationId, fuelType],
    queryFn: () => fetchPriceHistory(stationId, fuelType),
    enabled,
    staleTime: 15 * 60_000,
  });
}
