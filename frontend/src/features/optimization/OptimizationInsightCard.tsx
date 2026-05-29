import { Clock, Sparkles, TrafficCone, TrendingDown } from "lucide-react";
import { memo } from "react";

import type { RecommendationItem } from "@/features/recommendations/types";

import { OPTIMIZATION_PROFILES, rationaleFor, type OptimizationProfile } from "./types";

interface OptimizationInsightCardProps {
  items: RecommendationItem[] | undefined;
}

function profileLabel(profile: OptimizationProfile): string {
  return OPTIMIZATION_PROFILES.find((p) => p.value === profile)?.label ?? profile;
}

/**
 * Premium "why this pick" panel for the active optimization profile: rationale,
 * ETA, traffic delay and savings versus the runner-up. Renders only once an
 * optimized result set is available (top item carries the profile).
 */
export const OptimizationInsightCard = memo(function OptimizationInsightCard({
  items,
}: OptimizationInsightCardProps) {
  const top = items?.[0];
  const profile = top?.optimization_profile;
  if (!top || !profile) return null;

  const eta = top.eta_minutes;
  const trafficMin =
    top.traffic_delay_seconds != null ? top.traffic_delay_seconds / 60 : null;
  const runnerUp = items?.[1];
  const savings =
    runnerUp?.optimization_score != null && top.optimization_score != null
      ? runnerUp.optimization_score - top.optimization_score
      : null;

  return (
    <div className="rounded-xl border border-primary/20 bg-gradient-to-br from-primary/5 to-transparent p-3.5 motion-safe:animate-in motion-safe:fade-in">
      <div className="flex items-center gap-1.5">
        <Sparkles className="h-3.5 w-3.5 text-primary" aria-hidden />
        <span className="text-xs font-bold uppercase tracking-wide text-primary">
          Optimización · {profileLabel(profile)}
        </span>
      </div>

      <p className="mt-1.5 text-sm leading-snug text-foreground/90">
        {rationaleFor(profile)}
      </p>

      <div className="mt-2.5 flex flex-wrap gap-1.5">
        {eta != null && eta > 0 && (
          <Metric icon={<Clock className="h-3 w-3" aria-hidden />} label={`${eta.toFixed(0)} min`} />
        )}
        {trafficMin != null && trafficMin > 0 && (
          <Metric
            icon={<TrafficCone className="h-3 w-3" aria-hidden />}
            label={`+${trafficMin.toFixed(0)} min tráfico`}
            tone="amber"
          />
        )}
        {savings != null && savings > 0.005 && (
          <Metric
            icon={<TrendingDown className="h-3 w-3" aria-hidden />}
            label={`Ahorras ${savings.toFixed(2)} € vs. 2ª`}
            tone="green"
          />
        )}
      </div>
    </div>
  );
});

function Metric({
  icon,
  label,
  tone = "neutral",
}: {
  icon: React.ReactNode;
  label: string;
  tone?: "neutral" | "amber" | "green";
}) {
  const toneClass =
    tone === "amber"
      ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
      : tone === "green"
        ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
        : "bg-muted text-muted-foreground";
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold tabular-nums ${toneClass}`}
    >
      {icon}
      {label}
    </span>
  );
}
