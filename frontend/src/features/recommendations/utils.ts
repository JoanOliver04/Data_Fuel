import type { ConsumptionMode } from "@/features/vehicle-profile/types";

import type { RecommendationItem } from "./types";

// ── Opening-hours parser ────────────────────────────────────────────────────
// MITECO schedules look like "L-D: 24H", "L-D: 06:00-22:00", or multi-segment
// "L-V: 06:00-22:00; S: 07:00-22:00; D: 08:00-22:00". Day tokens are Spanish,
// Monday-indexed: L M X J V S D (X = Wednesday).
const ES_DAYS = ["L", "M", "X", "J", "V", "S", "D"] as const;

/** Set of Monday-indexed day numbers (0=Mon … 6=Sun) covered by a day-spec. */
function parseDaySpec(spec: string): Set<number> {
  const days = new Set<number>();
  const s = spec.trim().toUpperCase();
  if (!s) return days;
  if (s.includes("-")) {
    const parts = s.split("-");
    const a = ES_DAYS.indexOf((parts[0] ?? "").trim() as (typeof ES_DAYS)[number]);
    const b = ES_DAYS.indexOf((parts[1] ?? "").trim() as (typeof ES_DAYS)[number]);
    if (a < 0 || b < 0) return days;
    // Inclusive range; wrap defensively (e.g. a hypothetical "V-L").
    let i = a;
    for (let n = 0; n < 7; n++) {
      days.add(i);
      if (i === b) break;
      i = (i + 1) % 7;
    }
  } else {
    const i = ES_DAYS.indexOf(s as (typeof ES_DAYS)[number]);
    if (i >= 0) days.add(i);
  }
  return days;
}

/** Whether `minutes` (since midnight) falls in a time-spec like "06:00-22:00" / "24H". */
function timeSpecOpen(spec: string, minutes: number): boolean {
  const t = spec.trim().toUpperCase();
  if (t === "24H" || t === "24") return true;
  const m = t.match(/^(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})$/);
  if (!m) return false;
  const start = Number(m[1]) * 60 + Number(m[2]);
  let end = Number(m[3]) * 60 + Number(m[4]);
  if (end === 0) end = 1440; // a "00:00" close means midnight, not start-of-day
  if (end > start) return minutes >= start && minutes < end;
  return minutes >= start || minutes < end; // overnight range (e.g. 22:00-06:00)
}

/**
 * True if a station with this MITECO `schedule` string is open at `now`.
 * Unknown/unparseable schedules fail open (treated as open) so the "open now"
 * filter never hides a station we simply can't interpret.
 */
export function isStationOpenNow(schedule: string, now: Date = new Date()): boolean {
  if (!schedule || !schedule.trim()) return true;
  const esDay = (now.getDay() + 6) % 7; // JS Sun=0…Sat=6 → ES Mon=0…Sun=6
  const minutes = now.getHours() * 60 + now.getMinutes();
  let parsedAny = false;
  for (const segment of schedule.split(";")) {
    const idx = segment.indexOf(":");
    if (idx < 0) continue;
    const days = parseDaySpec(segment.slice(0, idx));
    if (days.size === 0) continue;
    parsedAny = true;
    if (days.has(esDay) && timeSpecOpen(segment.slice(idx + 1), minutes)) return true;
  }
  return parsedAny ? false : true;
}

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
