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
