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
