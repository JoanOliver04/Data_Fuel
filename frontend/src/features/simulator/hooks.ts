import { useQuery } from "@tanstack/react-query";

import { fetchRecommendations } from "@/features/recommendations/api";
import type { FuelType } from "@/types/fuel";

interface SimulatorDataParams {
  lat: number;
  lon: number;
  fuelType: FuelType;
}

/**
 * Fetches the maximum station snapshot (radius=40 km, up to 50 stations) for
 * a given location + fuel combination.  The result is cached for 10 minutes so
 * slider moves never trigger a network request — cost recalculation happens
 * entirely in the frontend via calcRealCost.
 *
 * liters=1 / km_cost=0 are sentinel values: we ignore the backend's total_cost
 * and only use price_per_liter + distance_km from the response.
 */
export function useSimulatorData(params: SimulatorDataParams | null) {
  return useQuery({
    queryKey: ["simulator-data", params],
    queryFn: () =>
      fetchRecommendations({
        lat: params!.lat,
        lon: params!.lon,
        liters: 1,
        fuel_type: params!.fuelType,
        km_cost: 0,
        max_distance_km: 40,
        limit: 50,
      }),
    enabled: params !== null,
    staleTime: 10 * 60_000,
    gcTime: 10 * 60_000,
  });
}
