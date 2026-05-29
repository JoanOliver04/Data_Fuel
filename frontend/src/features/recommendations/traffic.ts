import type { RecommendationItem } from "./types";

// ── Traffic & ETA domain layer ───────────────────────────────────────────────
// Pure, presentation-agnostic interpretation of the routing data the backend
// already returns (`driving_duration_min`, `traffic_delay_seconds`,
// `eta_minutes`). Everything downstream — badges, chips, popups — reads these
// derived types instead of re-deriving thresholds, so future capabilities
// (real-time guidance, traffic forecasting, departure-time hints) extend this
// module without touching the UI.

export type TrafficLevel = "free" | "light" | "moderate" | "heavy";

export interface TrafficStatus {
  level: TrafficLevel;
  /** Raw delay versus free-flow, in seconds. */
  delaySeconds: number;
  /** Delay rounded to whole minutes (0 when below a minute). */
  delayMinutes: number;
  /** Spanish, human-readable label, e.g. "Tráfico moderado". */
  label: string;
  /** Compact suffix shown next to the label, e.g. "+3 min" (empty for free). */
  delayLabel: string;
}

export interface EtaInfo {
  /** Driving time in minutes (rounded). */
  durationMin: number;
  /** Driving distance in km (road distance when available). */
  distanceKm: number;
  /** Short label, e.g. "8 min". */
  label: string;
}

// Below a minute, a delay is GPS/rounding noise — treated as free-flow. Mirrors
// TRAFFIC_BADGE_THRESHOLD_S in utils.ts so the two stay in lock-step.
const NOISE_S = 60;
// Absolute delay ceilings (seconds) per level.
const LIGHT_MAX_S = 180; // ≤ 3 min
const MODERATE_MAX_S = 360; // ≤ 6 min
// Delay-vs-freeflow ratios — a short trip with a small absolute delay can still
// be "heavy" in relative terms, so we take the worse of absolute and ratio.
const MODERATE_RATIO = 0.2;
const HEAVY_RATIO = 0.4;

const LEVEL_ORDER: Record<TrafficLevel, number> = {
  free: 0,
  light: 1,
  moderate: 2,
  heavy: 3,
};

const LEVEL_LABEL: Record<TrafficLevel, string> = {
  free: "Tráfico optimizado",
  light: "Tráfico ligero",
  moderate: "Tráfico moderado",
  heavy: "Tráfico denso",
};

function worse(a: TrafficLevel, b: TrafficLevel): TrafficLevel {
  return LEVEL_ORDER[a] >= LEVEL_ORDER[b] ? a : b;
}

function absoluteLevel(delay: number): TrafficLevel {
  if (delay <= NOISE_S) return "free";
  if (delay <= LIGHT_MAX_S) return "light";
  if (delay <= MODERATE_MAX_S) return "moderate";
  return "heavy";
}

function ratioLevel(delay: number, durationMin: number | null | undefined): TrafficLevel {
  if (durationMin == null || durationMin <= 0) return "free";
  // Approximate free-flow time = travel time minus the live-traffic delay.
  const freeFlowS = Math.max(durationMin * 60 - delay, 1);
  const ratio = delay / freeFlowS;
  if (ratio >= HEAVY_RATIO) return "heavy";
  if (ratio >= MODERATE_RATIO) return "moderate";
  return "light";
}

/**
 * Classify the live-traffic condition of a route. Returns `null` when the
 * provider gave no traffic data (haversine / ORS) — callers render nothing
 * rather than fabricate a status.
 */
export function classifyTraffic(item: RecommendationItem): TrafficStatus | null {
  const delay = item.traffic_delay_seconds;
  if (delay == null) return null;

  const level =
    delay <= NOISE_S
      ? "free"
      : worse(absoluteLevel(delay), ratioLevel(delay, item.driving_duration_min));

  const delayMinutes = delay > NOISE_S ? Math.round(delay / 60) : 0;
  return {
    level,
    delaySeconds: delay,
    delayMinutes,
    label: LEVEL_LABEL[level],
    delayLabel: delayMinutes > 0 ? `+${delayMinutes} min` : "",
  };
}

/**
 * Driving ETA for a station, or `null` when no driving duration is available
 * (haversine fallback). `eta_minutes` (optimization runs) is preferred when
 * present, otherwise the routing `driving_duration_min`.
 */
export function getEta(item: RecommendationItem): EtaInfo | null {
  const minutes = item.eta_minutes ?? item.driving_duration_min;
  if (minutes == null) return null;
  const durationMin = Math.round(minutes);
  return {
    durationMin,
    distanceKm: item.driving_distance_km ?? item.distance_km,
    label: `${durationMin} min`,
  };
}
