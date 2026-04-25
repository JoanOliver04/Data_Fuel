export type DrivingStyle = "urban" | "mixed" | "highway";

export interface VehicleProfile {
  id: number;
  name: string;
  fuel_consumption_per_100km: number;
  tank_capacity_litres: number;
  km_cost_per_km: number;
  driving_style: DrivingStyle;
  created_at: string;
}

export interface VehicleProfileCreate {
  name: string;
  fuel_consumption_per_100km: number;
  tank_capacity_litres: number;
  driving_style: DrivingStyle;
  reference_fuel_price?: number;
}

export interface VehicleProfileUpdate {
  name?: string;
  fuel_consumption_per_100km?: number;
  tank_capacity_litres?: number;
  driving_style?: DrivingStyle;
  reference_fuel_price?: number;
}

export interface KmCostEstimate {
  consumption_l_per_100km: number;
  fuel_price_eur_per_l: number;
  km_cost_eur_per_km: number;
}
