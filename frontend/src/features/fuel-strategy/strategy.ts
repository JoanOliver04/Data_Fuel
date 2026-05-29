import { deriveStationInsights, type StationInsight } from "@/features/recommendations/insights";
import { getEta } from "@/features/recommendations/traffic";
import type { RecommendationItem } from "@/features/recommendations/types";
import type { SmartAdvice } from "@/features/smart-advice/types";

import type {
  FuelStrategy,
  SavingsForecast,
  StrategyAction,
  StrategyReason,
  StrategyStation,
  StrategyTone,
} from "./types";

// ── Fuel Strategy engine ─────────────────────────────────────────────────────
// Pure, dependency-light synthesis: it never fetches, never mutates, and never
// fabricates. Every output is gated on a real, present signal. It *reuses* the
// existing recommendation insight engine (savings / tradeoff / structured
// badges) and traffic/ETA layer rather than re-deriving thresholds, and folds in
// the backend prediction verdict (SmartAdvice) for the time dimension.

/** Backend savings (in €) below which "waiting" isn't worth surfacing. */
const WAIT_MIN_SAVINGS = 0.5;
/** Predicted drop (%) above which we actively advise *against* refuelling today. */
const AVOID_DROP_PCT = 1.5;
/** Min |savings| (€) for a price-trend reason to be trustworthy (not noise). */
const TREND_MIN_SAVINGS = 0.3;
/** Below this many € a forecast figure is rounding noise — hidden. */
const FORECAST_EPS = 0.05;
/** A station this close (driving minutes) reads as "just around the corner". */
const NEARBY_MIN = 10;
/** Max reasons shown — keeps the card scannable. */
const MAX_REASONS = 4;

interface Decision {
  action: StrategyAction;
  tone: StrategyTone;
  headline: string;
  subline: string;
}

/**
 * Pick the single headline action by fusing the prediction verdict (WHEN to
 * refuel) with the ranked recommendation (WHERE/WHAT). Time signal wins when the
 * model expects a worthwhile drop; otherwise we commit to refuelling and point
 * at the best place.
 */
function decideAction(
  best: RecommendationItem,
  insight: StationInsight,
  advice: SmartAdvice | null,
): Decision {
  const waitWorthwhile = advice?.action === "WAIT" && advice.savings_eur > WAIT_MIN_SAVINGS;

  if (waitWorthwhile && advice) {
    const strongDrop = advice.savings_pct >= AVOID_DROP_PCT;
    return strongDrop
      ? {
          action: "AVOID_TODAY",
          tone: "wait",
          headline: "Evita repostar hoy",
          subline: "Se prevé una bajada notable de precios en los próximos días",
        }
      : {
          action: "WAIT",
          tone: "wait",
          headline: "Espera unos días",
          subline: "Repostar más adelante saldrá más barato",
        };
  }

  // Refuel now — decide whether the winner is worth a short detour ("visit
  // station X") or it's simply the best nearby ("refuel today").
  const detourWorthwhile =
    insight.tradeoff !== null ||
    (insight.savingsVsAvg !== null && insight.savingsVsAvg > best.travel_cost);

  return detourWorthwhile
    ? {
        action: "GO_TO_STATION",
        tone: "go",
        headline: `Reposta en ${best.brand}`,
        subline: "La mejor oportunidad está cerca de ti",
      }
    : {
        action: "REFUEL_TODAY",
        tone: "go",
        headline: "Reposta hoy",
        subline: "Es buen momento: no se prevén bajadas significativas",
      };
}

/**
 * Translate raw signals into trustworthy, plain-language bullets — the
 * user-friendly face of the prediction + XAI numbers. Reuses the recommendation
 * engine's *structured* outputs (badges / savings / tradeoff), never parsed
 * strings, so the two layers can never drift.
 */
function buildReasons(
  best: RecommendationItem,
  insight: StationInsight,
  advice: SmartAdvice | null,
): StrategyReason[] {
  const reasons: StrategyReason[] = [];
  const badgeIds = new Set(insight.badges.map((b) => b.id));

  // 1. Price trend (time) — the XAI signal in human terms. Only when clear.
  if (advice && advice.action === "WAIT" && advice.savings_eur >= TREND_MIN_SAVINGS) {
    reasons.push({
      id: "price-down",
      kind: "price-down",
      text: "Se prevé que los precios bajen pronto",
    });
  } else if (advice && advice.action === "REFUEL_NOW" && advice.savings_eur <= -TREND_MIN_SAVINGS) {
    reasons.push({
      id: "price-up",
      kind: "price-up",
      text: "Se prevé que los precios suban a corto plazo",
    });
  }

  // 2. Lowest total cost (place).
  if (badgeIds.has("lowest-total")) {
    reasons.push({ id: "cost", kind: "cost", text: "Ofrece el coste total de repostaje más bajo" });
  }

  // 3. Savings clearly beat the cost of getting there.
  if (insight.savings !== null && insight.savings > best.travel_cost) {
    reasons.push({
      id: "savings",
      kind: "savings",
      text: "El ahorro supera el coste del desplazamiento",
    });
  }

  // 4. Traffic favourable (only when peers are actually congested).
  if (badgeIds.has("traffic-optimized")) {
    reasons.push({ id: "traffic", kind: "traffic", text: "El tráfico está despejado en tu ruta" });
  }

  // 5. Genuinely close by.
  const eta = getEta(best);
  if (reasons.length < MAX_REASONS && eta !== null && eta.durationMin <= NEARBY_MIN) {
    reasons.push({ id: "distance", kind: "distance", text: "Está a pocos minutos en coche" });
  }

  return reasons.slice(0, MAX_REASONS);
}

/**
 * The two grounded savings figures: what choosing this station saves today (vs.
 * the set average) and what waiting could additionally save (backend forecast).
 * No speculative weekly/monthly extrapolation — only data we actually hold.
 */
function buildForecast(insight: StationInsight, advice: SmartAdvice | null): SavingsForecast {
  const today =
    insight.savingsVsAvg !== null && insight.savingsVsAvg > FORECAST_EPS
      ? insight.savingsVsAvg
      : null;
  const waiting =
    advice?.action === "WAIT" && advice.savings_eur > FORECAST_EPS ? advice.savings_eur : null;
  return { today, waiting };
}

/**
 * Build the flagship strategy from the data already on screen. Returns `null`
 * when there is nothing to advise (empty result set) so callers render nothing
 * rather than an empty shell.
 */
export function deriveStrategy(input: {
  items: RecommendationItem[];
  advice: SmartAdvice | null;
}): FuelStrategy | null {
  const best = input.items[0];
  if (best === undefined) return null;

  const insights = deriveStationInsights(input.items);
  const bestInsight = insights[0];
  if (bestInsight === undefined) return null;

  const advice = input.advice;
  const eta = getEta(best);
  const station: StrategyStation = {
    stationId: best.station_id,
    brand: best.brand,
    locality: best.locality,
    pricePerLiter: best.price_per_liter,
    totalCost: best.total_cost,
    etaMinutes: eta?.durationMin ?? null,
    distanceKm: eta?.distanceKm ?? best.driving_distance_km ?? best.distance_km,
  };

  const { action, tone, headline, subline } = decideAction(best, bestInsight, advice);

  return {
    action,
    tone,
    headline,
    subline,
    station,
    reasons: buildReasons(best, bestInsight, advice),
    forecast: buildForecast(bestInsight, advice),
    confidence: advice?.confidence ?? null,
  };
}
