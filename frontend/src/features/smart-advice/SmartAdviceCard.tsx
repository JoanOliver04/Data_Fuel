import { Brain, TrendingDown, TrendingUp, Minus } from "lucide-react";

import { cn } from "@/lib/utils";

import { useSmartAdvice } from "./hooks";
import type { SmartAdvice, SmartAdviceParams } from "./types";

// ── Skeleton ─────────────────────────────────────────────────────────────────

function SmartAdviceSkeleton() {
  return (
    <div className="animate-pulse rounded-2xl border border-border bg-background p-4">
      <div className="mb-3 h-3 w-36 rounded bg-muted" />
      <div className="mb-2 h-7 w-48 rounded bg-muted" />
      <div className="h-4 w-full rounded bg-muted" />
      <div className="mt-1.5 h-4 w-3/4 rounded bg-muted" />
    </div>
  );
}

// ── Card content ──────────────────────────────────────────────────────────────

function AdviceContent({ advice }: { advice: SmartAdvice }) {
  const isWait = advice.action === "WAIT";
  const hasSavings = advice.savings_eur > 0.5;
  const hasLoss = advice.savings_eur < -0.5;

  return (
    <div
      className={cn(
        "animate-in fade-in-0 slide-in-from-top-2 duration-300",
        "rounded-2xl border p-4",
        isWait
          ? "border-amber-200 bg-amber-50 dark:border-amber-800/40 dark:bg-amber-950/20"
          : "border-green-200 bg-green-50 dark:border-green-800/40 dark:bg-green-950/20",
      )}
    >
      {/* Header */}
      <div className="mb-2.5 flex items-center gap-1.5">
        <Brain className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
          Recomendación inteligente
        </span>
      </div>

      {/* Action */}
      <div
        className={cn(
          "mb-2 flex items-center gap-2 text-xl font-bold leading-none",
          isWait ? "text-amber-600 dark:text-amber-400" : "text-green-600 dark:text-green-400",
        )}
      >
        {isWait ? (
          <TrendingDown className="h-5 w-5 shrink-0" />
        ) : (
          <TrendingUp className="h-5 w-5 shrink-0" />
        )}
        {isWait ? "Esperar" : "Repostar ahora"}
      </div>

      {/* Savings highlight */}
      {hasSavings && (
        <div className="mb-2 inline-flex items-center gap-1 rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-semibold text-green-700 dark:bg-green-900/30 dark:text-green-400">
          Ahorro estimado: {advice.savings_eur.toFixed(2)} €
        </div>
      )}
      {hasLoss && (
        <div className="mb-2 inline-flex items-center gap-1 rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-semibold text-red-600 dark:bg-red-900/30 dark:text-red-400">
          <Minus className="h-3 w-3" />
          Esperar costaría {Math.abs(advice.savings_eur).toFixed(2)} € más
        </div>
      )}

      {/* Reasoning */}
      <p className="text-sm text-foreground/80">{advice.reasoning}</p>

      {/* Station + confidence footer */}
      <div className="mt-2.5 flex items-center justify-between border-t pt-2.5 text-xs text-muted-foreground">
        <span>
          {advice.recommended_station.brand} · {advice.recommended_station.locality} ·{" "}
          {advice.recommended_station.price_per_liter.toFixed(3)} €/L
        </span>
        <span className="shrink-0">
          Confianza: {Math.round(advice.confidence * 100)}%
        </span>
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
