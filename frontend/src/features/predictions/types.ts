export interface PredictionResult {
  station_id: number;
  fuel_type: string;
  current_price: number;
  predicted_price: number;
  change_pct: number;
  advice: string;
  horizon_hours: number;
  model_r2: number;
}
