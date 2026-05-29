import { getEta } from "@/features/recommendations/traffic";
import type { RecommendationItem } from "@/features/recommendations/types";

// ── Comparison metric registry ───────────────────────────────────────────────
// The single source of truth for *what* gets compared. Each metric is a pure,
// self-describing descriptor: how to read the value, whether lower is better,
// how to format it, and the award it confers when a station wins it. The
// comparison engine and the UI both iterate this list, so adding a future metric
// (carbon impact, loyalty discount, price volatility, forecast confidence) is a
// single append here — no engine or UI change required.

/** Stable icon key — mapped to a lucide icon in the presentation layer. */
export type AwardIcon = "fuel" | "wallet" | "navigation" | "zap" | "traffic" | "trophy";

export interface MetricDef {
  id: string;
  /** Row label in the comparison grid. */
  label: string;
  /** Short badge shown on the winning station, e.g. "Más barato". */
  award: string;
  awardIcon: AwardIcon;
  /** All current metrics are costs/times → lower is better. */
  lowerIsBetter: boolean;
  /** Comparable numeric value, or `null` when this station lacks the datum. */
  value: (item: RecommendationItem) => number | null;
  /** Cell text for an already-extracted value. */
  format: (value: number | null) => string;
}

function fmt(value: number | null, fn: (n: number) => string): string {
  return value === null ? "—" : fn(value);
}

export const COMPARISON_METRICS: readonly MetricDef[] = [
  {
    id: "price",
    label: "Precio",
    award: "Más barato",
    awardIcon: "fuel",
    lowerIsBetter: true,
    value: (i) => i.price_per_liter,
    format: (v) => fmt(v, (n) => `${n.toFixed(3)} €/L`),
  },
  {
    id: "total",
    label: "Coste total",
    award: "Mejor coste total",
    awardIcon: "wallet",
    lowerIsBetter: true,
    value: (i) => i.total_cost,
    format: (v) => fmt(v, (n) => `${n.toFixed(2)} €`),
  },
  {
    id: "distance",
    label: "Distancia",
    award: "Más cerca",
    awardIcon: "navigation",
    lowerIsBetter: true,
    value: (i) => getEta(i)?.distanceKm ?? i.driving_distance_km ?? i.distance_km,
    format: (v) => fmt(v, (n) => `${n.toFixed(1)} km`),
  },
  {
    id: "eta",
    label: "Tiempo",
    award: "Más rápida",
    awardIcon: "zap",
    lowerIsBetter: true,
    value: (i) => getEta(i)?.durationMin ?? null,
    format: (v) => fmt(v, (n) => `${n} min`),
  },
  {
    id: "traffic",
    label: "Tráfico",
    award: "Menos tráfico",
    awardIcon: "traffic",
    lowerIsBetter: true,
    value: (i) => i.traffic_delay_seconds ?? null,
    format: (v) => (v === null ? "—" : v <= 60 ? "Despejado" : `+${Math.round(v / 60)} min`),
  },
  {
    id: "score",
    label: "Puntuación",
    award: "Mejor valor",
    awardIcon: "trophy",
    lowerIsBetter: true,
    value: (i) => i.optimization_score ?? null,
    format: (v) => fmt(v, (n) => `${n.toFixed(2)} €`),
  },
] as const;
