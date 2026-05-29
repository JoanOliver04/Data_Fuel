import { Car, ChevronDown, ChevronUp, Heart, Info } from "lucide-react";
import { lazy, memo, Suspense, useCallback, useEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { FavoriteButton } from "@/features/favorites/FavoriteButton";
import { usePriceHistory } from "@/features/price-history/hooks";
import { PredictionBadge } from "@/features/predictions/PredictionBadge";
import { useSettingsStore } from "@/stores/settings.store";

import { deriveStationInsights, type StationInsight } from "./insights";
import {
  BadgeRow,
  EtaPill,
  InsightChips,
  SavingsHighlight,
  TradeoffNote,
  TrafficBadge,
  WhyRecommended,
} from "./RecommendationInsights";
import { RecommendationSkeleton } from "./RecommendationSkeleton";
import { classifyTraffic, getEta } from "./traffic";
import type { RecommendationItem } from "./types";
import { formatRealCostTooltip } from "./utils";

const STAGGER_STEP_MS = 35;
const STAGGER_MAX_STEPS = 8;

const PriceHistoryChart = lazy(() =>
  import("@/features/price-history/PriceHistoryChart").then((m) => ({
    default: m.PriceHistoryChart,
  })),
);

// ── Rank badge ───────────────────────────────────────────────────────────────

function rankBadgeClass(rank: number): string {
  if (rank === 1)
    return "bg-gradient-to-br from-amber-300 via-amber-400 to-amber-600 ring-2 ring-amber-300/40 shadow-md shadow-amber-400/30";
  if (rank === 2) return "bg-gradient-to-br from-slate-200 via-slate-300 to-slate-500";
  if (rank === 3) return "bg-gradient-to-br from-orange-300 via-orange-400 to-orange-700";
  return "bg-primary";
}

// ── Optimization breakdown cell ──────────────────────────────────────────────

function BreakdownCell({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <p className="text-muted-foreground">{label}</p>
      <p className="mt-0.5 font-semibold tabular-nums">{value.toFixed(2)}</p>
    </div>
  );
}

// ── Station card ─────────────────────────────────────────────────────────────

interface StationCardProps {
  item: RecommendationItem;
  rank: number;
  insight: StationInsight;
  isSelected: boolean;
  onSelect: (id: number) => void;
  onHover: (id: number | null) => void;
}

const StationCard = memo(function StationCard({
  item,
  rank,
  insight,
  isSelected,
  onSelect,
  onHover,
}: StationCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const hasProfile = useSettingsStore((s) => s.activeVehicleProfileId !== null);
  const [showChart, setShowChart] = useState(false);
  const { data: history } = usePriceHistory(item.station_id, item.fuel_type, showChart);

  const eta = getEta(item);
  const traffic = classifyTraffic(item);
  const distanceKm = item.driving_distance_km ?? item.distance_km;
  const enterDelay = `${Math.min(rank - 1, STAGGER_MAX_STEPS) * STAGGER_STEP_MS}ms`;

  useEffect(() => {
    if (isSelected && cardRef.current) {
      cardRef.current.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [isSelected]);

  return (
    <div
      ref={cardRef}
      role="button"
      tabIndex={0}
      onClick={() => onSelect(item.station_id)}
      onKeyDown={(e) => e.key === "Enter" && onSelect(item.station_id)}
      onMouseEnter={() => onHover(item.station_id)}
      onMouseLeave={() => onHover(null)}
      style={{ animationDelay: enterDelay }}
      className={cn(
        "group cursor-pointer rounded-2xl border p-4 transition-all duration-150",
        "fill-mode-both motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-1 motion-safe:duration-300",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring active:scale-[0.99]",
        isSelected
          ? "border-primary/40 bg-primary/5 shadow-sm ring-2 ring-primary/15"
          : insight.isBest
            ? "border-amber-300/60 bg-gradient-to-br from-amber-50/60 to-card shadow-md shadow-amber-500/5 hover:-translate-y-0.5 hover:shadow-lg dark:border-amber-400/25 dark:from-amber-950/20"
            : "border-border bg-card hover:-translate-y-0.5 hover:border-primary/25 hover:shadow-md hover:shadow-black/5",
      )}
    >
      {/* ── Recommendation badges (status — top of hierarchy) ── */}
      {insight.badges.length > 0 && (
        <div className="mb-2.5">
          <BadgeRow badges={insight.badges} />
        </div>
      )}

      {/* ── Top row: rank + info + price ── */}
      <div className="flex items-start gap-3">
        {/* Medal rank badge */}
        <span
          className={cn(
            "flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[11px] font-bold text-white transition-transform",
            rankBadgeClass(rank),
          )}
        >
          {rank}
        </span>

        {/* Station info */}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5 leading-none">
            <span className="truncate text-[15px] font-semibold">{item.brand}</span>
            <PredictionBadge stationId={item.station_id} fuelType={item.fuel_type} />
            <FavoriteButton stationId={item.station_id} />
          </div>
          <p className="mt-1 truncate text-xs text-muted-foreground">
            {item.locality}, {item.province}
          </p>
          <p className="mt-0.5 truncate text-[11px] text-muted-foreground/60">{item.address}</p>
        </div>

        {/* Total cost — right aligned */}
        <div className="shrink-0 text-right">
          <p className="text-[19px] font-bold leading-none tabular-nums tracking-tight">
            {item.total_cost.toFixed(2)} €
          </p>
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <p className="mt-1 flex cursor-default items-center justify-end gap-0.5 text-[10px] font-medium text-muted-foreground">
                  total
                  <Info className="h-3 w-3" aria-hidden />
                </p>
              </TooltipTrigger>
              <TooltipContent side="left">
                {formatRealCostTooltip(item, hasProfile)}
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      </div>

      {/* ── Savings highlight (second in hierarchy) ── */}
      {insight.savings != null && (
        <div className="mt-2.5">
          <SavingsHighlight amount={insight.savings} featured={insight.isBest} />
        </div>
      )}

      {/* ── Stats grid ── */}
      <div className="mt-3 grid grid-cols-3 divide-x divide-border rounded-xl border bg-muted/30 text-xs">
        <div className="px-2.5 py-2">
          <p className="text-[10px] font-medium text-muted-foreground">Precio</p>
          <p className="mt-1 font-semibold tabular-nums">
            {item.price_per_liter.toFixed(3)} €/L
          </p>
        </div>
        <div className="px-2.5 py-2">
          <p className="text-[10px] font-medium text-muted-foreground">Trayecto</p>
          <p className="mt-1 flex items-center gap-1 font-semibold tabular-nums">
            <Car className="h-3 w-3 shrink-0 text-muted-foreground" aria-hidden />
            {distanceKm.toFixed(1)} km
          </p>
          {(eta || (traffic && traffic.level !== "free")) && (
            <div className="mt-1.5 flex flex-wrap gap-1">
              {eta && <EtaPill label={eta.label} />}
              {traffic && traffic.level !== "free" && <TrafficBadge status={traffic} />}
            </div>
          )}
        </div>
        <div className="px-2.5 py-2">
          <p className="text-[10px] font-medium text-muted-foreground">Desglose</p>
          <p className="mt-1 font-semibold tabular-nums">
            {item.fuel_cost.toFixed(2)}+{item.travel_cost.toFixed(2)} €
          </p>
        </div>
      </div>

      {/* ── Optimization breakdown ── */}
      {item.optimization_score != null && (
        <div className="mt-2.5 rounded-xl border border-primary/15 bg-primary/[0.03] p-3">
          <div className="grid grid-cols-4 gap-1 text-center text-[10px]">
            <BreakdownCell label="Comb." value={item.fuel_cost} />
            <BreakdownCell label="Trayecto" value={item.travel_cost} />
            <BreakdownCell label="Tiempo" value={item.time_cost ?? 0} />
            <BreakdownCell label="Tráfico" value={item.traffic_penalty ?? 0} />
          </div>
          <div className="mt-2 flex items-center justify-between border-t border-primary/15 pt-2">
            <span className="text-[10px] font-medium text-muted-foreground">
              Puntuación
            </span>
            <span className="text-xs font-bold tabular-nums text-primary">
              {item.optimization_score.toFixed(2)} €
            </span>
          </div>
        </div>
      )}

      {/* ── Why this station? (best) / tradeoff + comparative chips (rest) ── */}
      {insight.isBest ? (
        <WhyRecommended reasons={insight.reasons} />
      ) : (
        <>
          {insight.tradeoff && <TradeoffNote text={insight.tradeoff} />}
          <InsightChips insight={insight} />
        </>
      )}

      {/* ── Price history toggle ── */}
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          setShowChart((p) => !p);
        }}
        aria-expanded={showChart}
        aria-label="Mostrar historial de precios"
        className="mt-3 flex min-h-[36px] w-full items-center justify-center gap-1.5 rounded-xl py-2 text-[11px] font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
      >
        {showChart ? (
          <ChevronUp className="h-3.5 w-3.5" />
        ) : (
          <ChevronDown className="h-3.5 w-3.5" />
        )}
        {showChart ? "Ocultar historial" : "Ver historial de precios"}
      </button>

      {showChart && (
        <div
          className="mt-1.5 rounded-xl border bg-muted/30 p-3"
          onClick={(e) => e.stopPropagation()}
        >
          <Suspense
            fallback={
              <p className="py-4 text-center text-xs text-muted-foreground">
                Cargando gráfica…
              </p>
            }
          >
            <PriceHistoryChart data={history ?? []} />
          </Suspense>
        </div>
      )}
    </div>
  );
});

// ── StationList ──────────────────────────────────────────────────────────────

interface StationListProps {
  items: RecommendationItem[] | undefined;
  isLoading: boolean;
  isError: boolean;
  hasSearched: boolean;
  selectedStationId: number | null;
  onStationSelect: (id: number | null) => void;
  onStationHover: (id: number | null) => void;
}

export function StationList({
  items,
  isLoading,
  isError,
  hasSearched,
  selectedStationId,
  onStationSelect,
  onStationHover,
}: StationListProps) {
  const favorites = useSettingsStore((s) => s.favorites);
  const [showOnlyFavorites, setShowOnlyFavorites] = useState(false);

  const handleSelect = useCallback(
    (id: number) => {
      onStationSelect(selectedStationId === id ? null : id);
    },
    [selectedStationId, onStationSelect],
  );

  if (!hasSearched) {
    return (
      <div className="flex flex-col items-center gap-4 px-4 py-16 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-muted text-3xl">
          📍
        </div>
        <div>
          <p className="font-semibold">¿Dónde quieres repostar?</p>
          <p className="mt-1 max-w-[240px] text-sm text-muted-foreground">
            Pulsa el icono de ubicación o escribe tu ciudad.
          </p>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-3 p-4 motion-safe:animate-in motion-safe:fade-in">
        <RecommendationSkeleton />
        <RecommendationSkeleton />
        <RecommendationSkeleton />
        <RecommendationSkeleton />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="px-4 py-10 text-center">
        <p className="text-sm font-medium text-destructive">Error al obtener resultados.</p>
        <p className="mt-1 text-xs text-muted-foreground">
          Comprueba que el backend está disponible.
        </p>
      </div>
    );
  }

  if (!items || items.length === 0) {
    return (
      <p className="px-4 py-8 text-center text-sm text-muted-foreground">
        No se encontraron gasolineras. Prueba a mover el mapa o ajusta los filtros.
      </p>
    );
  }

  const hasFavorites = items.some((item) => favorites.includes(item.station_id));
  const displayed = showOnlyFavorites
    ? items.filter((item) => favorites.includes(item.station_id))
    : items;
  const hasDrivingDistances = items.some((item) => item.driving_distance_km != null);

  // Smart-recommendation signals derived from the full ranked set (badges,
  // savings, rationale). Aligned by index with `displayed`.
  const insights = deriveStationInsights(displayed);

  return (
    <div className="flex h-full flex-col">
      {/* List header */}
      <div className="flex items-center justify-between border-b px-4 py-3">
        <div>
          <p className="text-sm font-semibold">
            {items.length} gasolinera{items.length !== 1 ? "s" : ""}
          </p>
          {hasDrivingDistances && (
            <p className="text-[10px] text-muted-foreground/70">Por carretera</p>
          )}
        </div>
        {hasFavorites && (
          <button
            type="button"
            onClick={() => setShowOnlyFavorites((p) => !p)}
            aria-pressed={showOnlyFavorites}
            className={cn(
              "flex min-h-[36px] items-center gap-1.5 rounded-full px-3.5 py-1.5 text-xs font-semibold transition-all duration-150",
              showOnlyFavorites
                ? "bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400"
                : "bg-muted text-muted-foreground hover:bg-muted/80",
            )}
          >
            <Heart
              className={cn("h-3.5 w-3.5", showOnlyFavorites && "fill-rose-500 text-rose-500")}
            />
            Favoritos
          </button>
        )}
      </div>

      {/* Scrollable list */}
      <div className="flex-1 space-y-2.5 overflow-y-auto overscroll-contain p-3 pb-4">
        {displayed.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">
            Ninguna gasolinera favorita en los resultados.
          </p>
        ) : (
          displayed.map((item, i) => (
            <StationCard
              key={item.station_id}
              item={item}
              rank={i + 1}
              insight={insights[i]!}
              isSelected={selectedStationId === item.station_id}
              onSelect={handleSelect}
              onHover={onStationHover}
            />
          ))
        )}
      </div>
    </div>
  );
}
