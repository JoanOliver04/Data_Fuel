import { apiFetch } from "@/lib/api-client";

import type { PricePoint } from "./types";

export async function fetchPriceHistory(
  stationId: number,
  fuelType: string,
  days = 30,
): Promise<PricePoint[]> {
  return apiFetch<PricePoint[]>(
    `/api/v1/stations/${stationId}/price-history/${fuelType}?days=${days}`,
  );
}
