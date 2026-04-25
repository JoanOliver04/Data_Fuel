import { Car, Heart } from "lucide-react";
import { memo, useCallback, useEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";
import { FavoriteButton } from "@/features/favorites/FavoriteButton";
import { PredictionBadge } from "@/features/predictions/PredictionBadge";
import { useSettingsStore } from "@/stores/settings.store";

import { RecommendationSkeleton } from "./RecommendationSkeleton";
import type { RecommendationItem } from "./types";
import { formatDrivingSummary } from "./utils";

// ── Rank badge helpers ───────────────────────────────────────────────────────

function rankBadgeClass(rank: number): string {
  if (rank === 1)
    return "bg-gradient-to-br from-amber-300 via-amber-400 to-amber-600 ring-2 ring-amber-300/40 shadow-md shadow-amber-400/30";
  if (rank === 2) return "bg-gradient-to-br from-slate-200 via-slate-300 to-slate-500";
  if (rank === 3) return "bg-gradient-to-br from-orange-300 via-orange-400 to-orange-700";
  return "bg-primary";
}

// ── Station card ─────────────────────────────────────────────────────────────

interface StationCardProps {
  item: RecommendationItem;
  rank: number;
  isSelected: boolean;
  onSelect: (id: number) => void;
  onHover: (id: number | null) => void;
}

const StationCard = memo(function StationCard({
  item,
  rank,
  isSelected,
  onSelect,
  onHover,
}: StationCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);

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
      className={cn(
        "group cursor-pointer rounded-xl border p-3.5 transition-all duration-150",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        isSelected
          ? "border-primary/40 bg-primary/5 shadow-sm ring-2 ring-primary/15"
          : "border-border bg-card hover:-translate-y-0.5 hover:border-primary/25 hover:shadow-md hover:shadow-black/5",
      )}
    >
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
            <span className="truncate font-semibold">{item.brand}</span>
            <PredictionBadge stationId={item.station_id} fuelType={item.fuel_type} />
            <FavoriteButton stationId={item.station_id} />
          </div>
          <p className="mt-0.5 truncate text-xs text-muted-foreground">
            {item.locality}, {item.province}
          </p>
          <p className="truncate text-[11px] text-muted-foreground/60">{item.address}</p>
        </div>

        {/* Total cost — right aligned */}
        <div className="shrink-0 text-right">
          <p className="text-[18px] font-bold leading-none tabular-nums tracking-tight">
            {item.total_cost.toFixed(2)} €
          </p>
          <p className="mt-0.5 text-[10px] font-medium text-muted-foreground">total</p>
        </div>
      </div>

      {/* Stats grid */}
      <div className="mt-2.5 grid grid-cols-3 divide-x divide-border border-t pt-2.5 text-xs">
        <div className="pr-2">
          <p className="text-muted-foreground">Precio</p>
          <p className="mt-0.5 font-semibold tabular-nums">
            {item.price_per_liter.toFixed(3)} €/L
          </p>
        </div>
        <div className="px-2">
          <p className="text-muted-foreground">Trayecto</p>
          <p className="mt-0.5 flex items-center gap-1 font-semibold">
            <Car className="h-3 w-3 shrink-0 text-muted-foreground" aria-hidden />
            {formatDrivingSummary(item)}
          </p>
        </div>
        <div className="pl-2">
          <p className="text-muted-foreground">Desglose</p>
          <p className="mt-0.5 font-semibold tabular-nums">
            {item.fuel_cost.toFixed(2)}+{item.travel_cost.toFixed(2)} €
          </p>
        </div>
      </div>
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
      <div className="space-y-2.5 p-4">
        <RecommendationSkeleton />
        <RecommendationSkeleton />
        <RecommendationSkeleton />
        <RecommendationSkeleton />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="px-4 py-8 text-center">
        <p className="text-sm font-medium text-destructive">Error al obtener resultados.</p>
        <p className="mt-1 text-xs text-muted-foreground">
          Comprueba que el backend está disponible.
        </p>
      </div>
    );
  }

  if (!items || items.length === 0) {
    return (
      <p className="px-4 py-6 text-center text-sm text-muted-foreground">
        No se encontraron gasolineras. Prueba a mover el mapa o ajusta los filtros.
      </p>
    );
  }

  const hasFavorites = items.some((item) => favorites.includes(item.station_id));
  const displayed = showOnlyFavorites
    ? items.filter((item) => favorites.includes(item.station_id))
    : items;
  const hasDrivingDistances = items.some((item) => item.driving_distance_km != null);

  return (
    <div className="flex h-full flex-col">
      {/* List header */}
      <div className="flex items-center justify-between border-b px-4 py-2.5">
        <div>
          <p className="text-sm font-medium">
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
              "flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold transition-all duration-150",
              showOnlyFavorites
                ? "bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400"
                : "bg-muted text-muted-foreground hover:bg-muted/80",
            )}
          >
            <Heart
              className={cn("h-3 w-3", showOnlyFavorites && "fill-rose-500 text-rose-500")}
            />
            Favoritos
          </button>
        )}
      </div>

      {/* Scrollable list */}
      <div className="flex-1 space-y-2 overflow-y-auto p-3">
        {displayed.length === 0 ? (
          <p className="py-4 text-center text-sm text-muted-foreground">
            Ninguna gasolinera favorita en los resultados.
          </p>
        ) : (
          displayed.map((item, i) => (
            <StationCard
              key={item.station_id}
              item={item}
              rank={i + 1}
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
