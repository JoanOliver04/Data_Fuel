import type { FuelType } from "@/types/fuel";

/** Direction of a feature's local effect on the predicted next-week price. */
export type ImpactDirection = "lowers" | "raises";

export interface FeatureImportanceItem {
  feature: string;
  display_name: string;
  description: string;
  /** Normalized importance percentage (the full set sums to ~100). */
  importance: number;
}

export interface GlobalFeatureImportance {
  features: FeatureImportanceItem[];
  feature_count: number;
  model_trained_at: string | null;
  model_version: string | null;
  model_r2: number | null;
  model_mae: number | null;
}

export interface ShapFactor {
  feature: string;
  display_name: string;
  /** Signed SHAP impact in €/L. Negative lowers the price, positive raises it. */
  impact: number;
  direction: ImpactDirection;
}

/** Same shape as the AI refuel-advice request — the explain endpoint reuses it. */
export interface ExplainRecommendationRequest {
  lat: number;
  lon: number;
  fuel_type: FuelType;
  municipio: string;
  station_lat: number;
  station_lon: number;
  precio_actual: number;
}

export interface ExplainRecommendationResponse {
  veredicto: "REPOSTA AHORA" | "ESPERA";
  prediction: number;
  base_value: number;
  precio_actual: number;
  variacion_pct: number;
  /** Model confidence (time-split R²), 0–1. */
  confidence: number;
  reasoning: string;
  shap_available: boolean;
  /** Strongest price-lowering factors (impact < 0). */
  top_positive_factors: ShapFactor[];
  /** Strongest price-raising factors (impact > 0). */
  top_negative_factors: ShapFactor[];
  /** Complete signed attribution, ordered by absolute impact. */
  feature_importance_local: ShapFactor[];
  feature_importance_global: FeatureImportanceItem[];
}
