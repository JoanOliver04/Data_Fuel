import { CheckCircle, Clock, TrendingDown, TrendingUp, X } from "lucide-react";

import { cn } from "@/lib/utils";

import type { AiRecommendationResponse } from "../types";

interface AiAdviceCardProps {
  response: AiRecommendationResponse;
  onDismiss?: () => void;
}

export function AiAdviceCard({ response, onDismiss }: AiAdviceCardProps) {
  const isRefuelNow = response.veredicto === "REPOSTA AHORA";
  const priceDrop = response.variacion_pct < 0;
  const confidencePct = Math.round(response.confianza * 100);
  const absPct = Math.abs(response.variacion_pct).toFixed(1);

  return (
    <div
      className={cn(
        "animate-in fade-in-0 slide-in-from-top-3 duration-300",
        "relative rounded-xl border-2 p-4",
        isRefuelNow
          ? "border-emerald-300 bg-emerald-50 dark:border-emerald-700/50 dark:bg-emerald-950/30"
          : "border-amber-300 bg-amber-50 dark:border-amber-700/50 dark:bg-amber-950/30",
      )}
    >
      {/* Dismiss button */}
      {onDismiss && (
        <button
          onClick={onDismiss}
          aria-label="Cerrar recomendación"
          className="absolute right-3 top-3 rounded-full p-0.5 text-muted-foreground/50 hover:text-muted-foreground"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      )}

      {/* Label */}
      <div className="mb-2 flex items-center gap-1.5">
        <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
          Predicción Random Forest · próxima semana
        </span>
      </div>

      {/* Veredicto headline */}
      <div
        className={cn(
          "mb-3 flex items-center gap-2 text-xl font-extrabold leading-none tracking-tight",
          isRefuelNow
            ? "text-emerald-700 dark:text-emerald-400"
            : "text-amber-600 dark:text-amber-400",
        )}
      >
        {isRefuelNow ? (
          <CheckCircle className="h-5 w-5 shrink-0" />
        ) : (
          <Clock className="h-5 w-5 shrink-0" />
        )}
        {response.veredicto}
      </div>

      {/* Price comparison row */}
      <div className="mb-3 flex items-center gap-3 rounded-lg bg-background/60 px-3 py-2.5 dark:bg-black/20">
        {/* Current price */}
        <div className="text-center">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
            Ahora
          </p>
          <p className="text-lg font-bold tabular-nums">
            {response.precio_actual.toFixed(3)}
            <span className="ml-0.5 text-xs font-normal text-muted-foreground">€/L</span>
          </p>
        </div>

        {/* Trend arrow */}
        <div className="flex flex-1 flex-col items-center">
          <div
            className={cn(
              "flex items-center gap-0.5 rounded-full px-2 py-0.5 text-xs font-bold",
              priceDrop
                ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400"
                : "bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400",
            )}
          >
            {priceDrop ? (
              <TrendingDown className="h-3 w-3" />
            ) : (
              <TrendingUp className="h-3 w-3" />
            )}
            {priceDrop ? "-" : "+"}
            {absPct}%
          </div>
          <div className="mt-1 h-px w-full bg-border" />
        </div>

        {/* Predicted price */}
        <div className="text-center">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
            7 días
          </p>
          <p
            className={cn(
              "text-lg font-bold tabular-nums",
              priceDrop
                ? "text-emerald-600 dark:text-emerald-400"
                : "text-red-600 dark:text-red-400",
            )}
          >
            {response.precio_predicho.toFixed(3)}
            <span className="ml-0.5 text-xs font-normal text-muted-foreground">€/L</span>
          </p>
        </div>
      </div>

      {/* Advice text */}
      <p className="mb-3 text-sm leading-relaxed text-foreground/80">{response.advice}</p>

      {/* Confidence bar */}
      <div className="space-y-1.5 border-t border-black/10 pt-3 dark:border-white/10">
        <div className="flex items-center justify-between text-xs">
          <span className="text-muted-foreground">Confianza del modelo (R²)</span>
          <span
            className={cn(
              "font-semibold tabular-nums",
              isRefuelNow
                ? "text-emerald-600 dark:text-emerald-400"
                : "text-amber-600 dark:text-amber-400",
            )}
          >
            {confidencePct}%
          </span>
        </div>
        <div className="h-1.5 overflow-hidden rounded-full bg-black/10 dark:bg-white/10">
          <div
            className={cn(
              "h-full rounded-full transition-all duration-700 ease-out",
              isRefuelNow ? "bg-emerald-500" : "bg-amber-500",
            )}
            style={{ width: `${confidencePct}%` }}
          />
        </div>
      </div>
    </div>
  );
}
