import type { FuelType } from "@/types/fuel";

export interface HeatmapParams {
  lat: number;
  lon: number;
  radius_km: number;
  fuel: FuelType;
}

export interface HeatmapProperties {
  id: number;
  /** Backend serialises Decimal as a string; we coerce on parse. */
  price: number;
  price_normalized: number;
  brand: string;
  name: string;
}

export interface HeatmapGeometry {
  type: "Point";
  /** GeoJSON convention: [longitude, latitude]. */
  coordinates: [number, number];
}

export interface HeatmapFeature {
  type: "Feature";
  geometry: HeatmapGeometry;
  properties: HeatmapProperties;
}

export interface HeatmapFeatureCollection {
  type: "FeatureCollection";
  features: HeatmapFeature[];
}
