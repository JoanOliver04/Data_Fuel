import { apiFetch } from "@/lib/api-client";

import type { HeatmapFeatureCollection, HeatmapParams } from "./types";

interface RawFeature {
  type: "Feature";
  geometry: { type: "Point"; coordinates: [number, number] };
  properties: {
    id: number;
    price: number | string;
    price_normalized: number;
    brand: string;
    name: string;
  };
}

interface RawCollection {
  type: "FeatureCollection";
  features: RawFeature[];
}

export async function fetchHeatmap(
  params: HeatmapParams,
): Promise<HeatmapFeatureCollection> {
  const qs = new URLSearchParams({
    lat: String(params.lat),
    lon: String(params.lon),
    radius_km: String(params.radius_km),
    fuel: params.fuel,
  });
  const raw = await apiFetch<RawCollection>(`/api/v1/stations/heatmap?${qs}`);
  // The backend serialises Decimal prices as strings; normalise to number on
  // entry so consumers don't have to remember to coerce in render paths.
  return {
    type: raw.type,
    features: raw.features.map((f) => ({
      type: f.type,
      geometry: f.geometry,
      properties: { ...f.properties, price: Number(f.properties.price) },
    })),
  };
}
