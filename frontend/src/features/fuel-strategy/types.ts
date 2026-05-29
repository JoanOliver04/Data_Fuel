// ── Fuel Strategy Assistant — domain types ───────────────────────────────────
// The presentation-agnostic contract for the flagship "what should I do?"
// decision. The engine ([strategy.ts]) fuses the prediction verdict (WHEN) with
// the ranked recommendation + insights (WHERE/WHAT) into a single FuelStrategy;
// the card ([FuelStrategyCard.tsx]) only renders it. New capabilities (price
// alerts, weekly planning, departure optimization) extend these types and the
// reason/forecast producers without touching the UI.

/** The single, headline action — the answer to "what should I do right now?". */
export type StrategyAction =
  | "REFUEL_TODAY" // good moment, refuel at the ranked winner
  | "GO_TO_STATION" // a clearly better station is worth the short trip
  | "WAIT" // the model expects a worthwhile price drop
  | "AVOID_TODAY"; // a notable drop is expected — don't refuel now

/** Visual intent — mapped to concrete colours in the presentation layer. */
export type StrategyTone = "go" | "wait";

/** Stable kind → drives the leading icon for a reason (presentation maps it). */
export type StrategyReasonKind =
  | "price-up"
  | "price-down"
  | "cost"
  | "distance"
  | "traffic"
  | "savings";

export interface StrategyReason {
  /** Stable key for React lists + future i18n. */
  id: string;
  kind: StrategyReasonKind;
  /** Short, human-readable, never exposes the underlying math. */
  text: string;
}

export interface SavingsForecast {
  /** € the recommended action saves today vs. the set average. `null` when not meaningful. */
  today: number | null;
  /** € that waiting could *additionally* save (backend prediction). `null` when N/A. */
  waiting: number | null;
}

/** The concrete object of the action — the station the user would drive to. */
export interface StrategyStation {
  stationId: number;
  brand: string;
  locality: string;
  pricePerLiter: number;
  totalCost: number;
  /** Driving minutes when routing data exists, else `null`. */
  etaMinutes: number | null;
  /** Road distance when available, else straight-line km. */
  distanceKm: number;
}

export interface FuelStrategy {
  action: StrategyAction;
  tone: StrategyTone;
  /** The bold answer, e.g. "Reposta hoy" / "Espera unos días". */
  headline: string;
  /** One supporting line — the rationale in plain language. */
  subline: string;
  /** The recommended station, or `null` when there is no result to point at. */
  station: StrategyStation | null;
  /** "Recomendado porque" bullets — ordered, capped, trustworthy. */
  reasons: StrategyReason[];
  forecast: SavingsForecast;
  /** Model confidence (time-split R²), 0–1. `null` when no prediction is available. */
  confidence: number | null;
}
