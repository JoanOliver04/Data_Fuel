// ── Smart Fuel Alerts — domain types ─────────────────────────────────────────
// Mirror of the backend alert API contract (backend/app/alerts/schemas.py). The
// frontend never invents alert shapes: these are the only objects that cross the
// /api/v1/alerts and /api/v1/notifications boundary. The presentation registry
// ([registry.tsx]) and the priority engine ([priority.ts]) build everything the
// UI shows on top of these — adding a backend alert type means adding one
// registry entry, never touching the wire types here.

import type { FuelType } from "@/types/fuel";

/** Server-defined alert kinds. Keep in lock-step with the backend `AlertType`. */
export type AlertType =
  | "PRICE_BELOW_THRESHOLD"
  | "PRICE_CHANGE"
  | "FAVORITE_STATION_CHANGE"
  | "CHEAPEST_BRAND"
  | "WEEKLY_SUMMARY"
  | "WAIT_VS_REFUEL_SIGNAL"
  | "PREDICTION_TREND"
  | "TOTAL_COST_DROP";

export type NotificationChannel = "in_app";
/** Whether the copy was deterministic or safely LLM-rephrased (never fabricated). */
export type TriggerSource = "deterministic" | "llm";

/** A stored, user-configured alert (backend `AlertOut`). */
export interface Alert {
  id: number;
  user_identifier: string;
  alert_type: AlertType;
  fuel_type: string;
  station_id: number | null;
  brand: string | null;
  threshold_price: string | null; // backend serialises Decimal as string
  threshold_pct: number | null;
  latitude: number | null;
  longitude: number | null;
  radius_km: number;
  liters: number;
  is_enabled: boolean;
  cooldown_minutes: number;
  last_triggered_at: string | null;
  created_at: string;
  updated_at: string;
}

/** Create payload (backend `AlertCreate`). Per-type required fields validated server-side. */
export interface AlertCreate {
  user_identifier: string;
  alert_type: AlertType;
  fuel_type: FuelType;
  station_id?: number;
  brand?: string;
  threshold_price?: number;
  threshold_pct?: number;
  latitude?: number;
  longitude?: number;
  radius_km?: number;
  liters?: number;
  cooldown_minutes?: number;
}

/** Partial update (backend `AlertUpdate`) — only mutable fields. */
export interface AlertUpdate {
  is_enabled?: boolean;
  threshold_price?: number;
  threshold_pct?: number;
  radius_km?: number;
  liters?: number;
  brand?: string;
  cooldown_minutes?: number;
}

/**
 * A delivered notification (backend `NotificationOut`). `data` is the structured,
 * already-validated payload the evaluator emitted — the priority engine reads its
 * numbers, never the prose, so the two layers can never drift.
 */
export interface AlertNotification {
  id: number;
  alert_id: number | null;
  user_identifier: string;
  alert_type: string;
  channel: NotificationChannel;
  title: string;
  message: string;
  source: TriggerSource;
  data: Record<string, unknown>;
  created_at: string;
}
