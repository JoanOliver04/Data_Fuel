import { getEta } from "@/features/recommendations/traffic";
import type { RecommendationItem } from "@/features/recommendations/types";

import { COMPARISON_METRICS, type AwardIcon } from "./metrics";

// ── Comparison engine ────────────────────────────────────────────────────────
// Pure cross-station analysis: per-metric winners, per-station awards, compact
// human insights and a deterministic AI-style summary. It never fetches and
// never fabricates — every output is gated on real values, and a metric where
// fewer than two stations carry data confers no winner. Driven entirely by the
// COMPARISON_METRICS registry, so it scales to new metrics for free.

const EPS = 1e-6;

export interface ComparisonCell {
  /** Rendered text (already formatted by the metric). */
  display: string;
  /** Raw comparable value, or null when absent. */
  value: number | null;
  /** True when this station wins the metric (and the metric is differentiating). */
  isWinner: boolean;
}

export interface ComparisonAward {
  metricId: string;
  label: string;
  icon: AwardIcon;
}

export interface ComparisonRow {
  metricId: string;
  label: string;
  cells: ComparisonCell[]; // index-aligned with `stations`
}

export interface ComparisonColumn {
  item: RecommendationItem;
  /** Awards this station won, in registry order. */
  awards: ComparisonAward[];
}

export interface ComparisonResult {
  stations: RecommendationItem[];
  columns: ComparisonColumn[];
  rows: ComparisonRow[];
  /** Compact, human-readable comparative facts (≤3). */
  insights: string[];
  /** Deterministic "AI comparison summary" paragraph. */
  summary: string;
}

function extreme<T>(arr: T[], key: (t: T) => number, lower: boolean): T {
  return arr.reduce((best, cur) => {
    const c = key(cur);
    const b = key(best);
    return (lower ? c < b : c > b) ? cur : best;
  });
}

/** Phrase fragment used by the summary to explain *why* a station wins. */
const AWARD_REASON: Record<string, string> = {
  total: "su menor coste total",
  eta: "su menor tiempo de viaje",
  distance: "su menor distancia",
  traffic: "su menor impacto del tráfico",
  score: "su mejor relación coste-tiempo",
};

function buildInsights(stations: RecommendationItem[]): string[] {
  const out: string[] = [];

  // Total-cost spread.
  const cheapestTotal = extreme(stations, (s) => s.total_cost, true);
  const dearestTotal = extreme(stations, (s) => s.total_cost, false);
  const totalDiff = dearestTotal.total_cost - cheapestTotal.total_cost;
  if (totalDiff > 0.01) {
    out.push(
      `${cheapestTotal.brand} es ${totalDiff.toFixed(2)} € más barata en total que ${dearestTotal.brand}`,
    );
  }

  // Driving-time spread (only across stations that expose an ETA).
  const withEta = stations
    .map((s) => ({ s, min: getEta(s)?.durationMin ?? null }))
    .filter((x): x is { s: RecommendationItem; min: number } => x.min !== null);
  if (withEta.length >= 2) {
    const fastest = extreme(withEta, (x) => x.min, true);
    const slowest = extreme(withEta, (x) => x.min, false);
    const minDiff = slowest.min - fastest.min;
    if (minDiff >= 1) {
      out.push(`${fastest.s.brand} ahorra ${minDiff} min de conducción frente a ${slowest.s.brand}`);
    }
  }

  // Best balance — the optimization-score winner, when it isn't simply the
  // cheapest-fuel station (otherwise the point is already obvious).
  const withScore = stations
    .map((s) => ({ s, v: s.optimization_score ?? null }))
    .filter((x): x is { s: RecommendationItem; v: number } => x.v !== null);
  if (withScore.length >= 2) {
    const balanced = extreme(withScore, (x) => x.v, true);
    const cheapestFuel = extreme(stations, (s) => s.price_per_liter, true);
    if (balanced.s.station_id !== cheapestFuel.station_id) {
      out.push(`${balanced.s.brand} ofrece el mejor equilibrio entre coste y tiempo`);
    }
  }

  return out.slice(0, 3);
}

function summarize(stations: RecommendationItem[], columns: ComparisonColumn[]): string {
  // Overall best: the optimization-score winner when profiles populated it,
  // otherwise the lowest total cost.
  const scored = stations.filter((s) => s.optimization_score != null);
  const best =
    scored.length > 0
      ? extreme(scored, (s) => s.optimization_score as number, true)
      : extreme(stations, (s) => s.total_cost, true);
  const cheapestFuel = extreme(stations, (s) => s.price_per_liter, true);

  const bestColumn = columns.find((c) => c.item.station_id === best.station_id);
  const reasons = (bestColumn?.awards ?? [])
    .map((a) => AWARD_REASON[a.metricId])
    .filter((r): r is string => r !== undefined);

  const because =
    reasons.length > 0
      ? `por ${reasons.slice(0, 2).join(" y ")}`
      : "por su mejor equilibrio general";

  if (best.station_id === cheapestFuel.station_id) {
    return `${best.brand} es la mejor opción: combina el precio de combustible más bajo con ${reasons[0] ?? "el mejor balance global"}.`;
  }
  return `Aunque ${cheapestFuel.brand} tiene el precio de combustible más bajo, ${best.brand} es la mejor opción global ${because}.`;
}

/**
 * Analyse a set of selected stations. Expects 2–3 stations; with fewer than two
 * it returns a no-winner result (the UI gates on length, this is a safety net).
 */
export function compareStations(stations: RecommendationItem[]): ComparisonResult {
  const columns: ComparisonColumn[] = stations.map((item) => ({ item, awards: [] }));

  const rows: ComparisonRow[] = COMPARISON_METRICS.map((metric) => {
    const values = stations.map((s) => metric.value(s));
    const finite = values.filter((v): v is number => v !== null);
    const canAward = finite.length >= 2; // need ≥2 data points to compare
    const best = canAward
      ? metric.lowerIsBetter
        ? Math.min(...finite)
        : Math.max(...finite)
      : null;

    let winners = values.map(
      (v) => best !== null && v !== null && Math.abs(v - best) <= EPS,
    );
    // A metric where everyone ties is not differentiating — drop the highlight.
    if (winners.every(Boolean)) winners = values.map(() => false);

    const cells: ComparisonCell[] = values.map((v, idx) => {
      const isWinner = winners[idx] ?? false;
      if (isWinner) {
        columns[idx]?.awards.push({ metricId: metric.id, label: metric.award, icon: metric.awardIcon });
      }
      return { value: v, display: metric.format(v), isWinner };
    });

    return { metricId: metric.id, label: metric.label, cells };
  });

  return {
    stations,
    columns,
    rows,
    insights: stations.length >= 2 ? buildInsights(stations) : [],
    summary: stations.length >= 2 ? summarize(stations, columns) : "",
  };
}
