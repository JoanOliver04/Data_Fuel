import {
  Fuel,
  MapPin,
  Sparkles,
  TrafficCone,
  TrendingDown,
  Trophy,
  Wallet,
  Zap,
  type LucideIcon,
} from "lucide-react";
import { memo } from "react";

import { cn } from "@/lib/utils";

import type { BadgeIcon, BadgeTone, RecommendationBadge, StationInsight } from "./insights";

// ── Tone & icon maps ─────────────────────────────────────────────────────────

const TONE_CLASS: Record<BadgeTone, string> = {
  gold: "bg-gradient-to-br from-amber-300/90 to-amber-500/90 text-amber-950 shadow-sm shadow-amber-500/30 dark:text-amber-50",
  green: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300",
  blue: "bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-300",
  violet: "bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300",
  emerald: "bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-300",
  amber: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
};

const ICON_MAP: Record<BadgeIcon, LucideIcon> = {
  trophy: Trophy,
  wallet: Wallet,
  fuel: Fuel,
  pin: MapPin,
  zap: Zap,
  traffic: TrafficCone,
  sparkles: Sparkles,
};

// ── Badge ────────────────────────────────────────────────────────────────────

function Badge({ badge }: { badge: RecommendationBadge }) {
  const Icon = ICON_MAP[badge.icon];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5",
        "text-[10px] font-bold uppercase leading-none tracking-wide",
        TONE_CLASS[badge.tone],
      )}
    >
      <Icon className="h-2.5 w-2.5 shrink-0" aria-hidden />
      {badge.label}
    </span>
  );
}

/** Horizontal, wrapping row of data-driven recommendation badges. */
export const BadgeRow = memo(function BadgeRow({
  badges,
}: {
  badges: RecommendationBadge[];
}) {
  if (badges.length === 0) return null;
  return (
    <div className="flex flex-wrap items-center gap-1">
      {badges.map((b) => (
        <Badge key={b.id} badge={b} />
      ))}
    </div>
  );
});

// ── Savings highlight ────────────────────────────────────────────────────────

/**
 * Prominent savings figure — the single number a user should notice first.
 * `featured` enlarges it for the top recommendation.
 */
export const SavingsHighlight = memo(function SavingsHighlight({
  amount,
  featured = false,
}: {
  amount: number;
  featured?: boolean;
}) {
  return (
    <div
      className={cn(
        "inline-flex items-center gap-1.5 rounded-xl px-2.5 py-1",
        "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/25 dark:text-emerald-300",
      )}
    >
      <TrendingDown
        className={cn("shrink-0", featured ? "h-4 w-4" : "h-3.5 w-3.5")}
        aria-hidden
      />
      <span className="font-medium leading-none">
        <span className="text-[10px] uppercase tracking-wide opacity-80">Ahorras </span>
        <span
          className={cn(
            "font-extrabold tabular-nums tracking-tight",
            featured ? "text-lg" : "text-sm",
          )}
        >
          {amount.toFixed(2)} €
        </span>
      </span>
    </div>
  );
});

// ── "Why this station?" panel ────────────────────────────────────────────────

/** Featured rationale panel for the best recommendation. */
export const WhyRecommended = memo(function WhyRecommended({
  reasons,
}: {
  reasons: string[];
}) {
  if (reasons.length === 0) return null;
  return (
    <div className="mt-3 rounded-xl border border-primary/15 bg-primary/[0.04] p-3">
      <div className="flex items-center gap-1.5">
        <Sparkles className="h-3 w-3 text-primary" aria-hidden />
        <span className="text-[10px] font-bold uppercase tracking-wide text-primary">
          ¿Por qué esta gasolinera?
        </span>
      </div>
      <ul className="mt-1.5 space-y-1">
        {reasons.map((reason) => (
          <li
            key={reason}
            className="flex items-start gap-1.5 text-xs leading-snug text-foreground/90"
          >
            <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-primary/70" aria-hidden />
            {reason}
          </li>
        ))}
      </ul>
    </div>
  );
});

// ── Comparative insight chips ────────────────────────────────────────────────

/** Compact, data-driven relative advantages shown on non-featured cards. */
export const InsightChips = memo(function InsightChips({
  insight,
}: {
  insight: StationInsight;
}) {
  const chips: string[] = [];
  if (insight.savingsVsAvg != null) {
    chips.push(`${insight.savingsVsAvg.toFixed(2)} € bajo la media`);
  }
  if (chips.length === 0) return null;
  return (
    <div className="mt-2 flex flex-wrap gap-1.5">
      {chips.map((c) => (
        <span
          key={c}
          className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-[10px] font-semibold tabular-nums text-muted-foreground"
        >
          <TrendingDown className="h-2.5 w-2.5" aria-hidden />
          {c}
        </span>
      ))}
    </div>
  );
});
