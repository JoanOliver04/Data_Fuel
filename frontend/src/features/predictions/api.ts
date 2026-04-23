import { ApiError, apiFetch } from "@/lib/api-client";

import type { PredictionResult } from "./types";

export async function fetchPrediction(
  stationId: number,
  fuelType: string,
): Promise<PredictionResult | null> {
  try {
    return await apiFetch<PredictionResult>(`/api/v1/predictions/${stationId}/${fuelType}`);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return null;
    throw e;
  }
}
