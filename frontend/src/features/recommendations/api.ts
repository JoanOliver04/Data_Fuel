import { apiFetch } from "@/lib/api-client";

import type { RecommendationItem, RecommendationParams } from "./types";

const NUMERIC_FIELDS = [
  "station_id",
  "latitude",
  "longitude",
  "price_per_liter",
  "liters",
  "distance_km",
  "km_cost",
  "fuel_cost",
  "travel_cost",
  "total_cost",
] as const satisfies readonly (keyof RecommendationItem)[];

const OPTIONAL_NUMERIC_FIELDS = [
  "driving_distance_km",
  "driving_duration_min",
] as const satisfies readonly (keyof RecommendationItem)[];

function normalize(item: RecommendationItem): RecommendationItem {
  const out = { ...item } as Record<string, unknown>;
  for (const key of NUMERIC_FIELDS) {
    out[key] = Number(item[key]);
  }
  for (const key of OPTIONAL_NUMERIC_FIELDS) {
    const raw = item[key];
    out[key] = raw === null || raw === undefined ? raw : Number(raw);
  }
  return out as unknown as RecommendationItem;
}

export async function fetchRecommendations(
  params: RecommendationParams,
): Promise<RecommendationItem[]> {
  const qs = new URLSearchParams({
    lat: String(params.lat),
    lon: String(params.lon),
    liters: String(params.liters),
    fuel_type: params.fuel_type,
  });
  if (params.limit !== undefined) qs.set("limit", String(params.limit));
  if (params.vehicle_profile_id !== undefined) {
    qs.set("vehicle_profile_id", String(params.vehicle_profile_id));
  } else if (params.km_cost !== undefined) {
    qs.set("km_cost", String(params.km_cost));
  }
  if (params.max_distance_km !== undefined) qs.set("max_distance_km", String(params.max_distance_km));
  if (params.north !== undefined) qs.set("north", String(params.north));
  if (params.south !== undefined) qs.set("south", String(params.south));
  if (params.east !== undefined) qs.set("east", String(params.east));
  if (params.west !== undefined) qs.set("west", String(params.west));

  const data = await apiFetch<RecommendationItem[]>(`/api/v1/recommendations?${qs}`);
  return data.map(normalize);
}
