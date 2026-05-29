import type { AlertNotification, AlertType } from "./types";

// ── Smart Fuel Alerts — prioritization engine ────────────────────────────────
// Pure, presentation-agnostic. It turns a delivered notification into the
// decision-oriented view-model the cards render: a priority level, the single
// recommended action, a savings figure and the station it concerns. Every value
// is read from the evaluator's *structured* `data` (never parsed from prose and
// never invented), so the engine can only surface figures the backend already
// computed from real prediction/recommendation data.

export type AlertPriority = "high" | "medium" | "info";

export interface AlertView {
  priority: AlertPriority;
  /** The single action the user should consider, or `null` for pure digests. */
  recommendation: string | null;
  /** Compact savings/impact figure, e.g. "≈ 2.4% más barato". `null` when N/A. */
  savingsLabel: string | null;
  /** The station/brand the alert points at, when the payload carries one. */
  stationLabel: string | null;
}

/** Magnitude (%) at/above which a forecast or change is treated as high priority. */
const HIGH_PCT = 2;
/** Below this (%) a movement is informational rather than actionable. */
const MED_PCT = 0.8;

const PRIORITY_RANK: Record<AlertPriority, number> = { high: 0, medium: 1, info: 2 };

function num(data: Record<string, unknown>, key: string): number | null {
  const v = data[key];
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

function str(data: Record<string, unknown>, key: string): string | null {
  const v = data[key];
  return typeof v === "string" && v.length > 0 ? v : null;
}

function pctLabel(pct: number): string {
  return `≈ ${Math.abs(pct).toFixed(1)}%`;
}

function byMagnitude(absPct: number): AlertPriority {
  if (absPct >= HIGH_PCT) return "high";
  if (absPct >= MED_PCT) return "medium";
  return "info";
}

/**
 * Derive the view-model for one notification. The mapping is exhaustive over the
 * known alert types; an unknown/future type degrades gracefully to an
 * informational card with no fabricated recommendation.
 */
export function deriveAlertView(n: AlertNotification): AlertView {
  const d = n.data;
  const type = n.alert_type as AlertType;

  switch (type) {
    case "PRICE_BELOW_THRESHOLD": {
      const price = num(d, "price");
      const target = num(d, "target");
      const savings =
        price !== null && target !== null && target > 0
          ? pctLabel(((target - price) / target) * 100)
          : null;
      return {
        priority: "high",
        recommendation: "Reposta ahora: ha alcanzado tu objetivo",
        savingsLabel: savings,
        stationLabel: str(d, "station"),
      };
    }

    case "TOTAL_COST_DROP": {
      const pct = num(d, "change_pct");
      return {
        priority: pct !== null ? byMagnitude(Math.abs(pct)) : "medium",
        recommendation: "Buen momento para repostar",
        savingsLabel: pct !== null ? `${pctLabel(pct)} más barato` : null,
        stationLabel: null,
      };
    }

    case "WAIT_VS_REFUEL_SIGNAL": {
      const save = num(d, "save_pct");
      return {
        priority: save !== null ? byMagnitude(save) : "medium",
        recommendation: "Espera unos días antes de repostar",
        savingsLabel: save !== null ? `${pctLabel(save)} de ahorro estimado` : null,
        stationLabel: null,
      };
    }

    case "PREDICTION_TREND": {
      const pct = num(d, "change_pct");
      const rising = pct !== null && pct > 0;
      return {
        priority: pct !== null ? byMagnitude(Math.abs(pct)) : "medium",
        recommendation: rising
          ? "Reposta antes de la subida prevista"
          : "Quizá compense esperar a que baje",
        savingsLabel: pct !== null ? pctLabel(pct) : null,
        stationLabel: null,
      };
    }

    case "CHEAPEST_BRAND": {
      const brand = str(d, "brand");
      return {
        priority: "medium",
        recommendation: brand ? `Reposta en ${brand}` : "Reposta en la marca indicada",
        savingsLabel: null,
        stationLabel: brand,
      };
    }

    case "PRICE_CHANGE": {
      const pct = num(d, "change_pct");
      const falling = pct !== null && pct < 0;
      return {
        priority: pct !== null ? byMagnitude(Math.abs(pct)) : "info",
        recommendation: falling ? "Precio a la baja: revisa la oportunidad" : null,
        savingsLabel: pct !== null ? pctLabel(pct) : null,
        stationLabel: str(d, "station"),
      };
    }

    case "FAVORITE_STATION_CHANGE": {
      const delta = num(d, "delta");
      const falling = delta !== null && delta < 0;
      return {
        priority: falling ? "medium" : "info",
        recommendation: falling ? "Tu estación favorita ha bajado de precio" : null,
        savingsLabel: delta !== null ? `${(Math.abs(delta) * 100).toFixed(0)} cént.` : null,
        stationLabel: str(d, "station"),
      };
    }

    case "WEEKLY_SUMMARY":
      return {
        priority: "info",
        recommendation: null,
        savingsLabel: null,
        stationLabel: str(d, "station"),
      };

    default:
      return { priority: "info", recommendation: null, savingsLabel: null, stationLabel: null };
  }
}

/** Sort notifications by priority, then most-recent first. Stable, non-mutating. */
export function sortByPriority(notifications: AlertNotification[]): AlertNotification[] {
  return [...notifications].sort((a, b) => {
    const pa = PRIORITY_RANK[deriveAlertView(a).priority];
    const pb = PRIORITY_RANK[deriveAlertView(b).priority];
    if (pa !== pb) return pa - pb;
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });
}

export const PRIORITY_META: Record<
  AlertPriority,
  { label: string; chip: string; dot: string }
> = {
  high: {
    label: "Prioridad alta",
    chip: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300",
    dot: "bg-red-500",
  },
  medium: {
    label: "Prioridad media",
    chip: "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300",
    dot: "bg-amber-500",
  },
  info: {
    label: "Informativa",
    chip: "bg-muted text-muted-foreground",
    dot: "bg-muted-foreground",
  },
};
