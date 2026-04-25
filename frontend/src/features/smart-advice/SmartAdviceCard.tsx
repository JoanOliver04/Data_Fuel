import { Brain, TrendingDown, TrendingUp, Minus } from "lucide-react";

import { cn } from "@/lib/utils";

import { useSmartAdvice } from "./hooks";
import type { SmartAdvice, SmartAdviceParams } from "./types";

// ── Skeleton ─────────────────────────────────────────────────────────────────

function SmartAdviceSkeleton() {
  return (
    <div className="animate-pulse rounded-xl border border-border bg-card p-4">
      <div className="mb-3 h-3 w-28 rounded-full bg-muted" />
      <div className="mb-2 h-6 w-40 rounded-full bg-muted" />
      <div className="space-y-1.5">
        <div className="h-3.5 w-full rounded-full bg-muted" />
        <div className="h-3.5 w-4/5 rounded-full bg-muted" />
      </div>
      <div className="mt-3 h-1.5 w-full rounded-full bg-muted" />
    </div>
  );
}

// ── Card content ──────────────────────────────────────────────────────────────

function AdviceContent({ advice }: { advice: SmartAdvice }) {
  const isWait = advice.action === "WAIT";
  const hasSavings = advice.savings_eur > 0.5;
  const hasLoss = advice.savings_eur < -0.5;
  const confidencePct = Math.round(advice.confidence * 100);

  return (
    <div
      className={cn(
        "animate-in fade-in-0 slide-in-from-top-2 duration-300",
        "rounded-xl border p-4",
        isWait
          ? "border-amber-200/70 bg-amber-50/80 dark:border-amber-800/30 dark:bg-amber-950/20"
          : "border-emerald-200/70 bg-emerald-50/80 dark:border-emerald-800/30 dark:bg-emerald-950/20",
      )}
    >
      {/* Header label */}
      <div className="mb-2 flex items-center gap-1.5">
        <Brain className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
          Recomendación IA
        </span>
      </div>

      {/* Action headline */}
      <div
        className={cn(
          "mb-2.5 flex items-center gap-2 text-[22px] font-extrabold leading-none tracking-tight",
          isWait
            ? "text-amber-600 dark:text-amber-400"
            : "text-emerald-600 dark:text-emerald-400",
        )}
      >
        {isWait ? (
          <TrendingDown className="h-5 w-5 shrink-0" />
        ) : (
          <TrendingUp className="h-5 w-5 shrink-0" />
        )}
        {isWait ? "Esperar" : "Repostar ahora"}
      </div>

      {/* Savings / loss badge */}
      {hasSavings && (
        <div className="mb-2.5 inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-semibold text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400">
          Ahorro estimado: {advice.savings_eur.toFixed(2)} €
        </div>
      )}
      {hasLoss && (
        <div className="mb-2.5 inline-flex items-center gap-1 rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-semibold text-red-600 dark:bg-red-900/30 dark:text-red-400">
          <Minus className="h-3 w-3" />
          Esperar costaría {Math.abs(advice.savings_eur).toFixed(2)} € más
        </div>
      )}

      {/* Reasoning */}
      <p className="text-sm leading-relaxed text-foreground/75">{advice.reasoning}</p>

      {/* Station + confidence */}
      <div className="mt-3 space-y-2 border-t pt-3">
        <div className="flex items-center justify-between text-xs">
          <span className="truncate text-muted-foreground">
            {advice.recommended_station.brand} · {advice.recommended_station.locality} ·{" "}
            {advice.recommended_station.price_per_liter.toFixed(3)} €/L
          </span>
          <span
            className={cn(
              "ml-2 shrink-0 font-semibold tabular-nums",
              isWait
                ? "text-amber-600 dark:text-amber-400"
                : "text-emerald-600 dark:text-emerald-400",
            )}
          >
            {confidencePct}%
          </span>
        </div>
        {/* Confidence progress bar */}
        <div className="h-1 overflow-hidden rounded-full bg-black/10 dark:bg-white/10">
          <div
            className={cn(
              "h-full rounded-full transition-all duration-700 ease-out",
              isWait ? "bg-amber-500" : "bg-emerald-500",
            )}
            style={{ width: `${confidencePct}%` }}
          />
        </div>
      </div>
    </div>
  );
}

// ── Public component ──────────────────────────────────────────────────────────

interface SmartAdviceCardProps {
  params: SmartAdviceParams | null;
}

export function SmartAdviceCard({ params }: SmartAdviceCardProps) {
  const { data, isLoading } = useSmartAdvice(params);

  if (!params) return null;
  if (isLoading) return <SmartAdviceSkeleton />;
  if (!data) return null;

  return <AdviceContent advice={data} />;
}
