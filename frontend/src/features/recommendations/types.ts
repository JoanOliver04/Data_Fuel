import type { FuelType } from "@/types/fuel";
import type { ConsumptionMode } from "@/features/vehicle-profile/types";

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
  driving_distance_km?: number | null;
  driving_duration_min?: number | null;
  consumption_mode?: ConsumptionMode | null;
  consumption_l_per_100km?: number | null;
}

export interface RecommendationParams {
  lat: number;
  lon: number;
  liters: number;
  fuel_type: FuelType;
  limit?: number;
  km_cost?: number;
  vehicle_profile_id?: number;
  max_distance_km?: number;
  /** Bounding box for map-based search. All four must be set together. */
  north?: number;
  south?: number;
  east?: number;
  west?: number;
}
