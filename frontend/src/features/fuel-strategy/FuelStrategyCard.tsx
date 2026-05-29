import {
  Bot,
  Clock,
  Fuel,
  MapPin,
  Navigation,
  ShieldCheck,
  Sparkles,
  TrendingDown,
  TrendingUp,
  Wallet,
} from "lucide-react";
import { memo, useMemo, type ReactNode } from "react";

import { cn } from "@/lib/utils";
import type { RecommendationItem } from "@/features/recommendations/types";
import { useSmartAdvice } from "@/features/smart-advice/hooks";
import type { SmartAdviceParams } from "@/features/smart-advice/types";

import { deriveStrategy } from "./strategy";
import type { FuelStrategy, StrategyReasonKind, StrategyTone } from "./types";

// ── Tone styling ─────────────────────────────────────────────────────────────
// Two intents only: "go" (act now, emerald) and "wait" (hold, amber). Mirrors
// the established SmartAdvice palette so the feature reads as a natural evolution.

interface ToneStyle {
  ring: string;
  glow: string;
  chip: string;
  headline: string;
  accentText: string;
  bar: string;
  Icon: typeof TrendingUp;
}

const TONE: Record<StrategyTone, ToneStyle> = {
  go: {
    ring: "ring-emerald-500/25",
    glow: "from-emerald-500/10 via-emerald-500/5",
    chip: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300",
    headline: "text-emerald-700 dark:text-emerald-300",
    accentText: "text-emerald-600 dark:text-emerald-400",
    bar: "bg-emerald-500",
    Icon: TrendingUp,
  },
  wait: {
    ring: "ring-amber-500/25",
    glow: "from-amber-500/10 via-amber-500/5",
    chip: "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300",
    headline: "text-amber-700 dark:text-amber-300",
    accentText: "text-amber-600 dark:text-amber-400",
    bar: "bg-amber-500",
    Icon: TrendingDown,
  },
};

const REASON_ICON: Record<StrategyReasonKind, ReactNode> = {
  "price-up": <TrendingUp className="h-3.5 w-3.5" aria-hidden />,
  "price-down": <TrendingDown className="h-3.5 w-3.5" aria-hidden />,
  cost: <Wallet className="h-3.5 w-3.5" aria-hidden />,
  distance: <Navigation className="h-3.5 w-3.5" aria-hidden />,
  traffic: <MapPin className="h-3.5 w-3.5" aria-hidden />,
  savings: <Sparkles className="h-3.5 w-3.5" aria-hidden />,
};

function confidenceLabel(confidence: number): string {
  if (confidence >= 0.7) return "Confianza alta";
  if (confidence >= 0.4) return "Confianza media";
  return "Orientativo";
}

// ── Skeleton ─────────────────────────────────────────────────────────────────

function StrategySkeleton() {
  return (
    <div className="animate-pulse rounded-2xl border border-border bg-card p-4">
      <div className="mb-3 h-3 w-40 rounded-full bg-muted" />
      <div className="mb-2 h-7 w-48 rounded-full bg-muted" />
      <div className="mb-4 h-3.5 w-56 rounded-full bg-muted" />
      <div className="space-y-2">
        <div className="h-3.5 w-full rounded-full bg-muted" />
        <div className="h-3.5 w-4/5 rounded-full bg-muted" />
      </div>
    </div>
  );
}

// ── Content ──────────────────────────────────────────────────────────────────

const StrategyContent = memo(function StrategyContent({ strategy }: { strategy: FuelStrategy }) {
  const tone = TONE[strategy.tone];
  const { station, forecast, reasons, confidence } = strategy;
  const confidencePct = confidence !== null ? Math.round(confidence * 100) : null;

  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-2xl border border-border bg-card shadow-elevation-lg ring-1",
        tone.ring,
        "motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-top-2 motion-safe:duration-500",
      )}
    >
      {/* Ambient tone glow */}
      <div
        aria-hidden
        className={cn("pointer-events-none absolute inset-x-0 -top-16 h-32 bg-gradient-to-b to-transparent blur-2xl", tone.glow)}
      />

      <div className="relative p-4">
        {/* Eyebrow */}
        <div className="mb-2.5 flex items-center gap-1.5">
          <span className="flex h-5 w-5 items-center justify-center rounded-md bg-primary/10">
            <Bot className="h-3.5 w-3.5 text-primary" aria-hidden />
          </span>
          <span className="text-[11px] font-bold uppercase tracking-widest text-muted-foreground">
            Asistente de estrategia
          </span>
        </div>

        {/* Headline action */}
        <h2
          className={cn(
            "flex items-center gap-2 text-2xl font-extrabold leading-none tracking-tight",
            tone.headline,
          )}
        >
          <tone.Icon className="h-6 w-6 shrink-0" aria-hidden />
          {strategy.headline}
        </h2>
        <p className="mt-2 text-sm leading-snug text-foreground/75">{strategy.subline}</p>

        {/* Savings forecast */}
        {(forecast.today !== null || forecast.waiting !== null) && (
          <div className="mt-3 flex flex-wrap gap-2">
            {forecast.today !== null && (
              <span className={cn("inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold tabular-nums", tone.chip)}>
                <Wallet className="h-3.5 w-3.5" aria-hidden />
                Hoy ahorras {forecast.today.toFixed(2)} €
              </span>
            )}
            {forecast.waiting !== null && (
              <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2.5 py-1 text-xs font-semibold tabular-nums text-amber-700 dark:bg-amber-900/40 dark:text-amber-300">
                <Clock className="h-3.5 w-3.5" aria-hidden />
                Esperar: +{forecast.waiting.toFixed(2)} €
              </span>
            )}
          </div>
        )}

        {/* Recommended station */}
        {station !== null && (
          <div className="mt-3.5 flex items-center gap-3 rounded-xl bg-muted/60 px-3 py-2.5">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-background shadow-sm">
              <Fuel className={cn("h-4 w-4", tone.accentText)} aria-hidden />
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold text-foreground">{station.brand}</p>
              <p className="truncate text-xs text-muted-foreground">
                {station.locality} · {station.pricePerLiter.toFixed(3)} €/L
                {station.etaMinutes !== null && ` · ${station.etaMinutes} min`}
              </p>
            </div>
            <div className="shrink-0 text-right">
              <p className="text-sm font-bold tabular-nums text-foreground">
                {station.totalCost.toFixed(2)} €
              </p>
              <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Total</p>
            </div>
          </div>
        )}

        {/* Reasons */}
        {reasons.length > 0 && (
          <div className="mt-3.5">
            <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              Recomendado porque
            </p>
            <ul className="space-y-1.5">
              {reasons.map((reason) => (
                <li key={reason.id} className="flex items-start gap-2 text-sm text-foreground/85">
                  <span className={cn("mt-0.5 shrink-0", tone.accentText)}>{REASON_ICON[reason.kind]}</span>
                  <span className="leading-snug">{reason.text}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Confidence footer */}
        {confidencePct !== null && (
          <div className="mt-3.5 border-t pt-3">
            <div className="flex items-center justify-between text-xs">
              <span className="inline-flex items-center gap-1 font-medium text-muted-foreground">
                <ShieldCheck className="h-3.5 w-3.5" aria-hidden />
                {confidenceLabel(confidence!)}
              </span>
              <span className={cn("font-semibold tabular-nums", tone.accentText)}>{confidencePct}%</span>
            </div>
            <div className="mt-1.5 h-1 overflow-hidden rounded-full bg-black/10 dark:bg-white/10">
              <div
                className={cn("h-full rounded-full transition-all duration-700 ease-out", tone.bar)}
                style={{ width: `${confidencePct}%` }}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
});

// ── Public component ──────────────────────────────────────────────────────────

interface FuelStrategyCardProps {
  /** Same params the SmartAdviceCard uses — the query is deduped, no extra fetch. */
  params: SmartAdviceParams | null;
  /** The ranked, already-processed result set from the page. */
  items: RecommendationItem[] | undefined;
}

/**
 * 🤖 Fuel Strategy Assistant — the flagship "what should I do?" card. It fuses
 * the prediction verdict with the live recommendation set into one actionable
 * decision. Resilient by design: it renders the place-based strategy as soon as
 * recommendations arrive and enriches it with the prediction once available.
 */
export function FuelStrategyCard({ params, items }: FuelStrategyCardProps) {
  const { data: advice, isLoading } = useSmartAdvice(params);

  const strategy = useMemo(
    () => deriveStrategy({ items: items ?? [], advice: advice ?? null }),
    [items, advice],
  );

  if (params === null) return null;
  if (strategy === null) return isLoading ? <StrategySkeleton /> : null;
  return <StrategyContent strategy={strategy} />;
}
