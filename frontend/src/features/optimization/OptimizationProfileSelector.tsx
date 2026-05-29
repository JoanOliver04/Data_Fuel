import { Coins, Gauge, Route, Scale } from "lucide-react";
import { memo } from "react";

import { cn } from "@/lib/utils";
import { useSettingsStore } from "@/stores/settings.store";

import { OPTIMIZATION_PROFILES, type OptimizationProfile } from "./types";

const ICONS: Record<OptimizationProfile, typeof Coins> = {
  CHEAPEST: Coins,
  BALANCED: Scale,
  FASTEST: Gauge,
  COMMUTER: Route,
};

/**
 * Segmented control for the active optimization profile. Persists to the
 * settings store; the recommendation query reads it and the backend re-ranks.
 */
export const OptimizationProfileSelector = memo(function OptimizationProfileSelector() {
  const active = useSettingsStore((s) => s.optimizationProfile);
  const setProfile = useSettingsStore((s) => s.setOptimizationProfile);

  return (
    <div
      role="radiogroup"
      aria-label="Perfil de optimización"
      className="grid grid-cols-4 gap-1 rounded-xl border border-border bg-muted/40 p-1"
    >
      {OPTIMIZATION_PROFILES.map(({ value, label }) => {
        const Icon = ICONS[value];
        const selected = active === value;
        return (
          <button
            key={value}
            type="button"
            role="radio"
            aria-checked={selected}
            onClick={() => setProfile(value)}
            className={cn(
              "flex flex-col items-center gap-1 rounded-lg px-1.5 py-2 text-[11px] font-semibold transition-all duration-150",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              selected
                ? "bg-background text-primary shadow-sm ring-1 ring-primary/20"
                : "text-muted-foreground hover:bg-background/60 hover:text-foreground",
            )}
          >
            <Icon className="h-3.5 w-3.5" aria-hidden />
            {label}
          </button>
        );
      })}
    </div>
  );
});
