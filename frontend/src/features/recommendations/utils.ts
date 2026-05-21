import type { ConsumptionMode } from "@/features/vehicle-profile/types";

import type { RecommendationItem } from "./types";

/** Returns "4.2 km · 8 min" when driving data is available, "4.2 km" otherwise. */
export function formatDrivingSummary(item: RecommendationItem): string {
  const km = item.driving_distance_km != null ? item.driving_distance_km : item.distance_km;
  const kmLabel = `${km.toFixed(1)} km`;
  if (item.driving_duration_min != null) {
    return `${kmLabel} · ${Math.round(item.driving_duration_min)} min`;
  }
  return kmLabel;
}

// Below this, traffic delay is noise (rounding/GPS jitter); only surface a badge
// once the live-traffic ETA penalty is at least a minute.
const TRAFFIC_BADGE_THRESHOLD_S = 60;

/**
 * Traffic-delay badge label like "+3 min" when the (TomTom) driving ETA carries
 * more than a minute of live-traffic delay; `null` when there is no meaningful
 * delay or the provider returned none (haversine / ORS).
 */
export function formatTrafficDelay(item: RecommendationItem): string | null {
  const delay = item.traffic_delay_seconds;
  if (delay == null || delay <= TRAFFIC_BADGE_THRESHOLD_S) return null;
  return `+${Math.round(delay / 60)} min`;
}

const MODE_LABEL_ES: Record<ConsumptionMode, string> = {
  urban: "urbano",
  mixed: "mixto",
  highway: "carretera",
};

/**
 * Tooltip text for the Real Cost badge.
 * - With profile + applied mode: "Basado en tu vehículo (consumo mixto): 0.09 €/km"
 * - With profile, no mode info:  "Tu vehículo: 0.105 €/km"
 * - Without profile:             "Coste por km: 0.130 €/km"
 */
export function formatRealCostTooltip(item: RecommendationItem, hasProfile: boolean): string {
  const km = Number(item.km_cost);
  if (hasProfile && item.consumption_mode) {
    const label = MODE_LABEL_ES[item.consumption_mode];
    return `Basado en tu vehículo (consumo ${label}): ${km.toFixed(2)} €/km`;
  }
  if (hasProfile) {
    return `Tu vehículo: ${km.toFixed(3)} €/km`;
  }
  return `Coste por km: ${km.toFixed(3)} €/km`;
}
