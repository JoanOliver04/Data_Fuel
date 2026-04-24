export interface SmartAdviceStation {
  station_id: number;
  brand: string;
  address: string;
  locality: string;
  province: string;
  latitude: number;
  longitude: number;
  price_per_liter: number;
  distance_km: number;
  total_cost: number;
}

export interface SmartAdvice {
  action: "REFUEL_NOW" | "WAIT";
  recommended_station: SmartAdviceStation;
  current_cost: number;
  predicted_cost: number;
  savings_eur: number;
  savings_pct: number;
  reasoning: string;
  confidence: number;
}

export interface SmartAdviceParams {
  lat: number;
  lon: number;
  fuel_type: string;
  liters?: number;
  km_cost?: number;
}
