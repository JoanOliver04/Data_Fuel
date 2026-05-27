import { ArrowDown, ArrowUp } from "lucide-react";

import { cn } from "@/lib/utils";

import type { ShapFactor } from "../types";

interface ShapImpactListProps {
  factors: ShapFactor[];
  /** Cap on rendered rows (factors arrive pre-sorted by |impact|). */
  max?: number;
}

/**
 * Per-feature SHAP impacts as a diverging magnitude list.
 *
 *   ↓ green  → factor lowers the predicted future price (good for "wait")
 *   ↑ red    → factor raises the predicted future price
 *
 * Bar width is proportional to |impact| relative to the strongest factor shown,
 * so the visual weight matches the model's attribution.
 */
export function ShapImpactList({ factors, max = 8 }: ShapImpactListProps) {
  const shown = factors.slice(0, max);
  if (shown.length === 0) {
    return (
      <p className="py-3 text-center text-xs text-muted-foreground">
        Desglose por factor no disponible.
      </p>
    );
  }

  const maxAbs = Math.max(...shown.map((f) => Math.abs(f.impact)), 1e-6);

  return (
    <ul className="space-y-1.5" aria-label="Impacto de cada factor en el precio previsto">
      {shown.map((factor) => {
        const lowers = factor.direction === "lowers";
        const widthPct = Math.max(4, (Math.abs(factor.impact) / maxAbs) * 100);
        return (
          <li key={factor.feature} className="flex items-center gap-2 text-xs">
            <span
              className={cn(
                "flex h-5 w-5 shrink-0 items-center justify-center rounded-md",
                lowers
                  ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400"
                  : "bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400",
              )}
              aria-hidden="true"
            >
              {lowers ? <ArrowDown className="h-3 w-3" /> : <ArrowUp className="h-3 w-3" />}
            </span>
            <span className="w-36 shrink-0 truncate text-foreground/80" title={factor.display_name}>
              {factor.display_name}
            </span>
            <span className="relative h-2 flex-1 overflow-hidden rounded-full bg-muted">
              <span
                className={cn(
                  "absolute inset-y-0 left-0 rounded-full transition-[width] duration-500 ease-out",
                  lowers ? "bg-emerald-500" : "bg-red-500",
                )}
                style={{ width: `${widthPct}%` }}
              />
            </span>
            <span
              className={cn(
                "w-14 shrink-0 text-right font-semibold tabular-nums",
                lowers
                  ? "text-emerald-600 dark:text-emerald-400"
                  : "text-red-600 dark:text-red-400",
              )}
            >
              {factor.impact > 0 ? "+" : ""}
              {factor.impact.toFixed(3)}
            </span>
          </li>
        );
      })}
    </ul>
  );
}
