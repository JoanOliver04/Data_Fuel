import {
  Bell,
  CalendarDays,
  Clock,
  Fuel,
  Star,
  Target,
  TrendingDown,
  TrendingUp,
  Wallet,
  type LucideIcon,
} from "lucide-react";

import type { AlertType } from "./types";

// ── Smart Fuel Alerts — presentation registry ────────────────────────────────
// The single declarative seam that maps each server alert type to its UI. It
// mirrors the backend's declarative evaluator/`_REQUIRED_FIELDS` design: adding a
// future alert type (traffic windows, loyalty savings, multi-station, behaviour)
// is one entry here — the Alert Center, the create flow and the cards all read
// from this map, so no component branches on the type. Nothing here fabricates
// data; it only describes how a type looks and which inputs it needs.

/** Grouping for the create flow tabs. */
export type AlertCategory = "price" | "ai" | "digest";

/** Extra inputs a type needs beyond fuel + location (collected by the form). */
export type AlertField = "threshold_price" | "threshold_pct" | "brand";

/** Colour intent, mapped to concrete classes in the cards. */
export type AlertTone = "emerald" | "amber" | "blue" | "violet" | "slate";

export interface AlertTypeMeta {
  type: AlertType;
  /** Full, human label — never the raw enum. */
  label: string;
  /** Short chip label for dense rows. */
  short: string;
  /** Friendly one-liner describing what the alert watches. */
  description: string;
  icon: LucideIcon;
  tone: AlertTone;
  category: AlertCategory;
  /** Inputs the create form must render for this type. */
  fields: AlertField[];
  /** Needs the user's coordinates (prefilled from settings). */
  needsGeo: boolean;
  /** Offered in the "create alert" flow. Digest/auto types may be hidden. */
  creatable: boolean;
}

export const ALERT_REGISTRY: Record<AlertType, AlertTypeMeta> = {
  PRICE_BELOW_THRESHOLD: {
    type: "PRICE_BELOW_THRESHOLD",
    label: "Precio por debajo de tu objetivo",
    short: "Objetivo de precio",
    description: "Avísame cuando el precio baje de un valor que yo elija.",
    icon: Target,
    tone: "emerald",
    category: "price",
    fields: ["threshold_price"],
    needsGeo: true,
    creatable: true,
  },
  CHEAPEST_BRAND: {
    type: "CHEAPEST_BRAND",
    label: "Una marca se vuelve la más barata",
    short: "Marca más barata",
    description: "Avísame cuando una marca cercana sea la opción más barata.",
    icon: Fuel,
    tone: "blue",
    category: "price",
    fields: ["brand"],
    needsGeo: true,
    creatable: true,
  },
  TOTAL_COST_DROP: {
    type: "TOTAL_COST_DROP",
    label: "Baja el coste total real",
    short: "Coste total",
    description: "Avísame cuando el coste total (combustible + viaje) caiga.",
    icon: Wallet,
    tone: "emerald",
    category: "price",
    fields: ["threshold_pct"],
    needsGeo: true,
    creatable: true,
  },
  PRICE_CHANGE: {
    type: "PRICE_CHANGE",
    label: "Cambio de precio relevante",
    short: "Cambio de precio",
    description: "Avísame cuando el precio se mueva más de un porcentaje en 7 días.",
    icon: TrendingUp,
    tone: "amber",
    category: "price",
    fields: ["threshold_pct"],
    needsGeo: true,
    creatable: true,
  },
  WAIT_VS_REFUEL_SIGNAL: {
    type: "WAIT_VS_REFUEL_SIGNAL",
    label: "Quizá compense esperar",
    short: "Esperar",
    description: "La predicción detecta una bajada cercana: te avisamos si vale la pena esperar.",
    icon: Clock,
    tone: "violet",
    category: "ai",
    fields: ["threshold_pct"],
    needsGeo: true,
    creatable: true,
  },
  PREDICTION_TREND: {
    type: "PREDICTION_TREND",
    label: "Tendencia de precio prevista",
    short: "Tendencia IA",
    description: "Avísame cuando la predicción anticipe una subida o bajada notable.",
    icon: TrendingDown,
    tone: "violet",
    category: "ai",
    fields: ["threshold_pct"],
    needsGeo: true,
    creatable: true,
  },
  FAVORITE_STATION_CHANGE: {
    type: "FAVORITE_STATION_CHANGE",
    label: "Tu estación favorita cambia de precio",
    short: "Favorita",
    description: "Avísame cuando una estación que sigo cambie de precio.",
    icon: Star,
    tone: "amber",
    category: "ai",
    fields: [],
    needsGeo: false,
    creatable: false, // created contextually from a favourite station
  },
  WEEKLY_SUMMARY: {
    type: "WEEKLY_SUMMARY",
    label: "Resumen semanal",
    short: "Resumen",
    description: "Un resumen semanal con la mejor opción para tu combustible.",
    icon: CalendarDays,
    tone: "slate",
    category: "digest",
    fields: [],
    needsGeo: true,
    creatable: true,
  },
};

/** Safe lookup — unknown/future server types fall back to a neutral descriptor. */
export function alertMeta(type: string): AlertTypeMeta {
  return (
    ALERT_REGISTRY[type as AlertType] ?? {
      type: type as AlertType,
      label: type,
      short: "Alerta",
      description: "",
      icon: Bell,
      tone: "slate",
      category: "digest",
      fields: [],
      needsGeo: false,
      creatable: false,
    }
  );
}

/** Tailwind classes per tone — kept here so cards stay declarative. */
export const TONE_CLASSES: Record<
  AlertTone,
  { chip: string; icon: string; ring: string; bar: string }
> = {
  emerald: {
    chip: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300",
    icon: "text-emerald-600 dark:text-emerald-400",
    ring: "ring-emerald-500/25",
    bar: "bg-emerald-500",
  },
  amber: {
    chip: "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300",
    icon: "text-amber-600 dark:text-amber-400",
    ring: "ring-amber-500/25",
    bar: "bg-amber-500",
  },
  blue: {
    chip: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
    icon: "text-blue-600 dark:text-blue-400",
    ring: "ring-blue-500/25",
    bar: "bg-blue-500",
  },
  violet: {
    chip: "bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300",
    icon: "text-violet-600 dark:text-violet-400",
    ring: "ring-violet-500/25",
    bar: "bg-violet-500",
  },
  slate: {
    chip: "bg-muted text-muted-foreground",
    icon: "text-muted-foreground",
    ring: "ring-border",
    bar: "bg-muted-foreground",
  },
};
