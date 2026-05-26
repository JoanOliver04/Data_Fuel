import type { FuelType } from "@/types/fuel";

export interface AiRecommendationRequest {
  lat: number;
  lon: number;
  fuel_type: FuelType;
  municipio: string;
  // comarca is resolved server-side from `municipio`; the client does not send it.
  precio_actual: number;
}

export interface AiRecommendationResponse {
  veredicto: "REPOSTA AHORA" | "ESPERA";
  precio_actual: number;
  precio_predicho: number;
  variacion_pct: number;
  advice: string;
  confianza: number;
}
