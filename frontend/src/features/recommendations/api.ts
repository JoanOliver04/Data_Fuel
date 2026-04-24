import { apiFetch } from "@/lib/api-client";

import type { RecommendationItem, RecommendationParams } from "./types";

export function fetchRecommendations(params: RecommendationParams): Promise<RecommendationItem[]> {
  const qs = new URLSearchParams({
    lat: String(params.lat),
    lon: String(params.lon),
    liters: String(params.liters),
    fuel_type: params.fuel_type,
  });
  if (params.limit !== undefined) qs.set("limit", String(params.limit));
  if (params.km_cost !== undefined) qs.set("km_cost", String(params.km_cost));
  if (params.max_distance_km !== undefined) qs.set("max_distance_km", String(params.max_distance_km));
  if (params.north !== undefined) qs.set("north", String(params.north));
  if (params.south !== undefined) qs.set("south", String(params.south));
  if (params.east !== undefined) qs.set("east", String(params.east));
  if (params.west !== undefined) qs.set("west", String(params.west));

  return apiFetch<RecommendationItem[]>(`/api/v1/recommendations?${qs}`);
}
