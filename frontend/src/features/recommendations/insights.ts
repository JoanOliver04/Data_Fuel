import type { RecommendationItem } from "./types";

// ── Smart recommendation engine ──────────────────────────────────────────────
// Pure, presentation-agnostic layer that turns a *ranked* result set into the
// human-facing signals the UI shows: data-driven badges, savings figures, a
// "recommended because" rationale and comparative insight chips.
//
// It never fabricates data — every signal is gated on the underlying numbers
// being present and meaningful. New recommendation types (eco, price-prediction,
// AI) plug in by adding a `BadgeRule` to BADGE_RULES; no UI change required.

/** Visual tone — mapped to concrete colours in the presentation layer. */
export type BadgeTone = "gold" | "green" | "blue" | "violet" | "emerald" | "amber";

/** Stable icon key — mapped to a lucide icon in the presentation layer. */
export type BadgeIcon =
  | "trophy"
  | "wallet"
  | "fuel"
  | "pin"
  | "zap"
  | "traffic"
  | "sparkles";

export type BadgeId =
  | "best"
  | "lowest-total"
  | "cheapest-fuel"
  | "closest"
  | "fastest"
  | "traffic-optimized"
  | "smart";

export interface RecommendationBadge {
  id: BadgeId;
  label: string;
  tone: BadgeTone;
  icon: BadgeIcon;
  /** Lower = higher priority when capping how many badges a card shows. */
  priority: number;
}

export interface StationInsight {
  /** Sorted by priority, ready to render. */
  badges: RecommendationBadge[];
  /** € saved vs. the most expensive option in the set (`null` when ≤ 0.01). */
  savings: number | null;
  /** € below the set average total cost (`null` when ≤ 0.01). */
  savingsVsAvg: number | null;
  /** Compact, human-readable "recommended because" bullets. */
  reasons: string[];
  /** True for the top-ranked station. */
  isBest: boolean;
}

/** Aggregate stats over the whole result set — computed once, shared by rules. */
interface InsightContext {
  count: number;
  rank: number; // 1-based position in the (already sorted) list
  minTotal: number;
  maxTotal: number;
  avgTotal: number;
  minPrice: number;
  minDistanceKm: number;
  minDuration: number | null;
  hasTrafficData: boolean;
  someoneHasTraffic: boolean;
}

const EPS = 1e-6;
/** A price within 0.5 % of the cheapest still reads as "very competitive". */
const PRICE_COMPETITIVE_RATIO = 1.005;
/** Below this many seconds, a traffic delay is GPS/rounding noise. */
const TRAFFIC_NOISE_S = 60;
/** Max badges rendered per card — keeps the scan clean. */
const MAX_BADGES = 3;

function drivingKm(item: RecommendationItem): number {
  return item.driving_distance_km ?? item.distance_km;
}

// ── Badge rules ──────────────────────────────────────────────────────────────
// Each rule is a pure predicate over (item, context). Order here is irrelevant;
// `priority` drives display order. To add a recommendation type, append a rule.

interface BadgeRule {
  id: BadgeId;
  tone: BadgeTone;
  icon: BadgeIcon;
  priority: number;
  label: (item: RecommendationItem, ctx: InsightContext) => string;
  applies: (item: RecommendationItem, ctx: InsightContext) => boolean;
}

const BADGE_RULES: readonly BadgeRule[] = [
  {
    id: "best",
    tone: "gold",
    icon: "trophy",
    priority: 0,
    label: () => "Mejor opción",
    applies: (_item, ctx) => ctx.rank === 1,
  },
  {
    id: "smart",
    tone: "violet",
    icon: "sparkles",
    priority: 1,
    // Surfaces only when the backend actually re-ranked by a profile.
    label: () => "Recomendación inteligente",
    applies: (item, ctx) => ctx.rank === 1 && item.optimization_profile != null,
  },
  {
    id: "lowest-total",
    tone: "green",
    icon: "wallet",
    priority: 2,
    label: () => "Coste total más bajo",
    applies: (item, ctx) => ctx.count > 1 && item.total_cost <= ctx.minTotal + EPS,
  },
  {
    id: "cheapest-fuel",
    tone: "blue",
    icon: "fuel",
    priority: 3,
    label: () => "Combustible más barato",
    applies: (item, ctx) =>
      ctx.count > 1 && item.price_per_liter <= ctx.minPrice + EPS,
  },
  {
    id: "fastest",
    tone: "blue",
    icon: "zap",
    priority: 4,
    label: () => "Ruta más rápida",
    applies: (item, ctx) =>
      ctx.count > 1 &&
      ctx.minDuration != null &&
      item.driving_duration_min != null &&
      item.driving_duration_min <= ctx.minDuration + EPS,
  },
  {
    id: "closest",
    tone: "violet",
    icon: "pin",
    priority: 5,
    label: () => "Más cercana",
    applies: (item, ctx) =>
      ctx.count > 1 && drivingKm(item) <= ctx.minDistanceKm + EPS,
  },
  {
    id: "traffic-optimized",
    tone: "emerald",
    icon: "traffic",
    priority: 6,
    label: () => "Tráfico optimizado",
    // Only meaningful when this route is clear *and* others are congested.
    applies: (item, ctx) =>
      ctx.someoneHasTraffic &&
      (item.traffic_delay_seconds == null ||
        item.traffic_delay_seconds <= TRAFFIC_NOISE_S),
  },
];

function buildContext(items: RecommendationItem[], rank: number): InsightContext {
  let minTotal = Infinity;
  let maxTotal = -Infinity;
  let sumTotal = 0;
  let minPrice = Infinity;
  let minDistanceKm = Infinity;
  let minDuration: number | null = null;
  let hasTrafficData = false;
  let someoneHasTraffic = false;

  for (const it of items) {
    if (it.total_cost < minTotal) minTotal = it.total_cost;
    if (it.total_cost > maxTotal) maxTotal = it.total_cost;
    sumTotal += it.total_cost;
    if (it.price_per_liter < minPrice) minPrice = it.price_per_liter;
    const km = drivingKm(it);
    if (km < minDistanceKm) minDistanceKm = km;
    if (it.driving_duration_min != null) {
      minDuration = minDuration == null ? it.driving_duration_min : Math.min(minDuration, it.driving_duration_min);
    }
    if (it.traffic_delay_seconds != null) {
      hasTrafficData = true;
      if (it.traffic_delay_seconds > TRAFFIC_NOISE_S) someoneHasTraffic = true;
    }
  }

  return {
    count: items.length,
    rank,
    minTotal,
    maxTotal,
    avgTotal: items.length > 0 ? sumTotal / items.length : 0,
    minPrice,
    minDistanceKm,
    minDuration,
    hasTrafficData,
    someoneHasTraffic,
  };
}

/**
 * Human-readable rationale for a station — calculations translated into
 * benefits. Compact (≤ 4 bullets) and ordered by importance. Used for the
 * featured "¿Por qué esta gasolinera?" panel.
 */
function buildReasons(
  item: RecommendationItem,
  ctx: InsightContext,
  savings: number | null,
): string[] {
  const reasons: string[] = [];
  const isLowestTotal = item.total_cost <= ctx.minTotal + EPS;

  if (isLowestTotal) {
    reasons.push("Coste total de repostaje más bajo");
  } else if (item.price_per_liter <= ctx.minPrice * PRICE_COMPETITIVE_RATIO) {
    reasons.push("Precio de combustible muy competitivo");
  }

  const km = drivingKm(item);
  if (km <= ctx.minDistanceKm + EPS) {
    reasons.push("Distancia de conducción corta");
  } else if (item.driving_duration_min != null && item.driving_duration_min <= 10) {
    reasons.push("A pocos minutos en coche");
  }

  if (
    ctx.someoneHasTraffic &&
    (item.traffic_delay_seconds == null ||
      item.traffic_delay_seconds <= TRAFFIC_NOISE_S)
  ) {
    reasons.push("Bajo impacto del tráfico");
  }

  if (savings != null && reasons.length < 4) {
    reasons.push(`Ahorras ${savings.toFixed(2)} € frente a la opción más cara`);
  }

  return reasons.slice(0, 4);
}

/** Build the per-station insight for one item given a prepared context. */
function insightFrom(item: RecommendationItem, ctx: InsightContext): StationInsight {
  const badges = BADGE_RULES.filter((rule) => rule.applies(item, ctx))
    .sort((a, b) => a.priority - b.priority)
    .slice(0, MAX_BADGES)
    .map<RecommendationBadge>((rule) => ({
      id: rule.id,
      label: rule.label(item, ctx),
      tone: rule.tone,
      icon: rule.icon,
      priority: rule.priority,
    }));

  const rawSavings = ctx.maxTotal - item.total_cost;
  const savings = ctx.count > 1 && rawSavings > 0.01 ? rawSavings : null;
  const rawVsAvg = ctx.avgTotal - item.total_cost;
  const savingsVsAvg = ctx.count > 1 && rawVsAvg > 0.01 ? rawVsAvg : null;

  return {
    badges,
    savings,
    savingsVsAvg,
    reasons: buildReasons(item, ctx, savings),
    isBest: ctx.rank === 1,
  };
}

/** Build the per-station insight for one item given its rank + the full set. */
export function deriveStationInsight(
  item: RecommendationItem,
  items: RecommendationItem[],
  rank: number,
): StationInsight {
  return insightFrom(item, buildContext(items, rank));
}

/**
 * Derive insights for a whole ranked list. Aggregate stats are computed once
 * (O(n)); only `rank` varies per item. Aligned by index with `items`
 * (index 0 = rank 1).
 */
export function deriveStationInsights(items: RecommendationItem[]): StationInsight[] {
  const base = buildContext(items, 1);
  return items.map((item, i) => insightFrom(item, { ...base, rank: i + 1 }));
}
