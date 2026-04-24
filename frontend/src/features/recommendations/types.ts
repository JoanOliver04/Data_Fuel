import type { FuelType } from "@/types/fuel";

export interface RecommendationItem {
  station_id: number;
  brand: string;
  address: string;
  locality: string;
  municipality: string;
  province: string;
  latitude: number;
  longitude: number;
  schedule: string;
  fuel_type: FuelType;
  price_per_liter: number;
  liters: number;
  distance_km: number;
  km_cost: number;
  fuel_cost: number;
  travel_cost: number;
  total_cost: number;
}

export interface RecommendationParams {
  lat: number;
  lon: number;
  liters: number;
  fuel_type: FuelType;
  limit?: number;
  km_cost?: number;
  max_distance_km?: number;
  /** Bounding box for map-based search. All four must be set together. */
  north?: number;
  south?: number;
  east?: number;
  west?: number;
}
