import {
  Bot,
  Fuel,
  Navigation,
  Scale,
  Sparkles,
  TrafficCone,
  Trophy,
  Wallet,
  X,
  Zap,
  type LucideIcon,
} from "lucide-react";
import { memo, useMemo, type CSSProperties } from "react";

import { cn } from "@/lib/utils";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { PredictionBadge } from "@/features/predictions/PredictionBadge";
import type { RecommendationItem } from "@/features/recommendations/types";

import { compareStations, type ComparisonResult } from "./comparison";
import type { AwardIcon } from "./metrics";
import { MAX_COMPARE_STATIONS, useComparisonStore } from "./store";

const AWARD_ICON: Record<AwardIcon, LucideIcon> = {
  fuel: Fuel,
  wallet: Wallet,
  navigation: Navigation,
  zap: Zap,
  traffic: TrafficCone,
  trophy: Trophy,
};

// ── Comparison grid ──────────────────────────────────────────────────────────
// A CSS-grid table: a sticky metric-label column + one column per station. The
// whole grid scrolls horizontally on narrow screens, so 3 columns stay readable
// down to 320px without truncating the metric a user is scanning.

const ComparisonGrid = memo(function ComparisonGrid({
  result,
  onRemove,
}: {
  result: ComparisonResult;
  onRemove: (id: number) => void;
}) {
  const n = result.stations.length;
  const gridStyle: CSSProperties = {
    gridTemplateColumns: `minmax(84px, 0.9fr) repeat(${n}, minmax(98px, 1fr))`,
  };

  return (
    <div className="overflow-x-auto overscroll-x-contain">
      <div className="grid min-w-full text-sm" style={gridStyle}>
        {/* Header row: corner + station headers */}
        <div className="sticky left-0 z-10 bg-popover" />
        {result.columns.map((col) => (
          <div
            key={col.item.station_id}
            className="border-b border-border px-2 pb-2.5 pt-1 text-center"
          >
            <div className="flex items-start justify-center gap-1">
              <span className="truncate text-[13px] font-bold leading-tight">{col.item.brand}</span>
              <button
                type="button"
                onClick={() => onRemove(col.item.station_id)}
                aria-label={`Quitar ${col.item.brand} de la comparación`}
                className="-mr-1 shrink-0 rounded-full p-0.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              >
                <X className="h-3 w-3" />
              </button>
            </div>
            <p className="truncate text-[10px] text-muted-foreground">{col.item.locality}</p>
            <div className="mt-1 flex justify-center">
              <PredictionBadge stationId={col.item.station_id} fuelType={col.item.fuel_type} />
            </div>
          </div>
        ))}

        {/* Metric rows */}
        {result.rows.map((row) => (
          <Row key={row.metricId} label={row.label} cells={row.cells} />
        ))}
      </div>
    </div>
  );
});

function Row({
  label,
  cells,
}: {
  label: string;
  cells: ComparisonResult["rows"][number]["cells"];
}) {
  return (
    <>
      <div className="sticky left-0 z-10 flex items-center border-b border-border/60 bg-popover px-2 py-2.5 text-[11px] font-medium text-muted-foreground">
        {label}
      </div>
      {cells.map((cell, idx) => (
        <div
          key={idx}
          className={cn(
            "flex items-center justify-center border-b border-border/60 px-2 py-2.5 text-center tabular-nums",
            cell.isWinner
              ? "bg-emerald-50 font-bold text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-300"
              : "text-foreground/90",
          )}
        >
          <span className="inline-flex items-center gap-1">
            {cell.isWinner && <Trophy className="h-3 w-3 shrink-0" aria-label="Mejor" />}
            {cell.display}
          </span>
        </div>
      ))}
    </>
  );
}

// ── Award chips, insights & AI summary ───────────────────────────────────────

function AwardStrip({ result }: { result: ComparisonResult }) {
  const winning = result.columns.filter((c) => c.awards.length > 0);
  if (winning.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-2 px-4 pt-3">
      {winning.map((col) =>
        col.awards.map((award) => {
          const Icon = AWARD_ICON[award.icon];
          return (
            <span
              key={`${col.item.station_id}-${award.metricId}`}
              className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2.5 py-1 text-[11px] font-bold text-amber-800 dark:bg-amber-900/30 dark:text-amber-300"
            >
              <Icon className="h-3 w-3 shrink-0" aria-hidden />
              {award.label}: {col.item.brand}
            </span>
          );
        }),
      )}
    </div>
  );
}

function InsightsBlock({ insights }: { insights: string[] }) {
  if (insights.length === 0) return null;
  return (
    <div className="px-4 pt-4">
      <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
        Comparativa
      </p>
      <ul className="space-y-1.5">
        {insights.map((text) => (
          <li key={text} className="flex items-start gap-2 text-sm text-foreground/90">
            <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" aria-hidden />
            <span className="leading-snug">{text}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function SummaryBlock({ summary }: { summary: string }) {
  if (!summary) return null;
  return (
    <div className="mx-4 mt-4 rounded-xl border border-primary/20 bg-gradient-to-br from-primary/5 to-transparent p-3.5">
      <div className="mb-1.5 flex items-center gap-1.5">
        <span className="flex h-5 w-5 items-center justify-center rounded-md bg-primary/10">
          <Bot className="h-3.5 w-3.5 text-primary" aria-hidden />
        </span>
        <span className="text-[11px] font-bold uppercase tracking-widest text-muted-foreground">
          Resumen IA
        </span>
      </div>
      <p className="text-sm leading-relaxed text-foreground/85">{summary}</p>
    </div>
  );
}

// ── Floating selection bar ───────────────────────────────────────────────────

function ComparisonBar({
  count,
  canCompare,
  onCompare,
  onClear,
}: {
  count: number;
  canCompare: boolean;
  onCompare: () => void;
  onClear: () => void;
}) {
  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-[76px] z-[60] flex justify-center px-4 lg:bottom-6">
      <div className="pointer-events-auto flex items-center gap-2 rounded-full border border-border bg-background/95 py-1.5 pl-4 pr-1.5 shadow-elevation-xl backdrop-blur-xl motion-safe:animate-in motion-safe:slide-in-from-bottom-3">
        <Scale className="h-4 w-4 shrink-0 text-primary" aria-hidden />
        <span className="text-sm font-semibold tabular-nums">
          {count}/{MAX_COMPARE_STATIONS}
        </span>
        <button
          type="button"
          onClick={onClear}
          aria-label="Vaciar comparación"
          className="rounded-full p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
        >
          <X className="h-4 w-4" />
        </button>
        <button
          type="button"
          onClick={onCompare}
          disabled={!canCompare}
          className={cn(
            "min-h-[40px] rounded-full px-4 text-sm font-semibold transition-all active:scale-95",
            canCompare
              ? "bg-primary text-primary-foreground hover:brightness-110"
              : "cursor-not-allowed bg-muted text-muted-foreground",
          )}
        >
          Comparar
        </button>
      </div>
    </div>
  );
}

// ── Public orchestrator ──────────────────────────────────────────────────────

interface ComparisonCenterProps {
  /** The current ranked, processed result set (source of truth for the data). */
  items: RecommendationItem[] | undefined;
}

/**
 * ⛽ Fuel Station Comparison Center — the floating selection bar plus the premium
 * side-by-side comparison dialog. Selection lives in the store; the data is read
 * back from `items` so columns always reflect the live recommendation set.
 */
export function ComparisonCenter({ items }: ComparisonCenterProps) {
  const compareIds = useComparisonStore((s) => s.compareIds);
  const isOpen = useComparisonStore((s) => s.isOpen);
  const open = useComparisonStore((s) => s.open);
  const close = useComparisonStore((s) => s.close);
  const remove = useComparisonStore((s) => s.remove);
  const clear = useComparisonStore((s) => s.clear);

  // Resolve ids → live items, preserving the user's add order; drop stale ids
  // (e.g. a station that fell out of the latest results).
  const selected = useMemo(() => {
    const byId = new Map((items ?? []).map((i) => [i.station_id, i]));
    return compareIds
      .map((id) => byId.get(id))
      .filter((i): i is RecommendationItem => i !== undefined);
  }, [items, compareIds]);

  const result = useMemo(
    () => (selected.length >= 2 ? compareStations(selected) : null),
    [selected],
  );

  const canCompare = selected.length >= 2;

  return (
    <>
      {selected.length > 0 && !isOpen && (
        <ComparisonBar
          count={selected.length}
          canCompare={canCompare}
          onCompare={open}
          onClear={clear}
        />
      )}

      <Dialog open={isOpen && result !== null} onOpenChange={(o) => (o ? open() : close())}>
        <DialogContent className="flex max-h-[88vh] w-[calc(100vw-1.5rem)] max-w-2xl flex-col overflow-hidden p-0">
          <div className="flex items-center gap-2 border-b border-border px-4 py-3.5">
            <Scale className="h-4 w-4 shrink-0 text-primary" aria-hidden />
            <DialogTitle className="text-base">Comparativa de gasolineras</DialogTitle>
          </div>

          {result !== null && (
            <div className="flex-1 overflow-y-auto overscroll-contain pb-5">
              <AwardStrip result={result} />
              <div className="mt-3 px-2">
                <ComparisonGrid result={result} onRemove={remove} />
              </div>
              <InsightsBlock insights={result.insights} />
              <SummaryBlock summary={result.summary} />
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
