import type { FuelType } from "@/types/fuel";

export interface AiRecommendationRequest {
  lat: number;
  lon: number;
  fuel_type: FuelType;
  municipio: string;
  // comarca is resolved server-side from `municipio`; the client does not send it.
  // Coordinates of the recommended station, so the server's `distancia` feature
  // matches training (Alzira→station) instead of using the user as a proxy.
  station_lat: number;
  station_lon: number;
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
