import { Car, Heart } from "lucide-react";
import { memo, useCallback, useEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";
import { FavoriteButton } from "@/features/favorites/FavoriteButton";
import { PredictionBadge } from "@/features/predictions/PredictionBadge";
import { useSettingsStore } from "@/stores/settings.store";

import { RecommendationSkeleton } from "./RecommendationSkeleton";
import type { RecommendationItem } from "./types";
import { formatDrivingSummary } from "./utils";

// ── Station card ────────────────────────────────────────────────────────────

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

  // Scroll into view when selected from map
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
        "group cursor-pointer rounded-2xl border p-3.5 transition-all duration-150",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        isSelected
          ? "border-primary/60 bg-primary/5 shadow-sm"
          : "border-border bg-background hover:border-primary/30 hover:bg-muted/40",
      )}
    >
      <div className="flex items-start gap-3">
        {/* Rank badge */}
        <span
          className={cn(
            "flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white transition-colors",
            rank === 1
              ? "bg-amber-500"
              : rank === 2
                ? "bg-slate-400"
                : rank === 3
                  ? "bg-amber-700"
                  : "bg-primary",
          )}
        >
          {rank}
        </span>

        {/* Info */}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5 leading-none">
            <span className="truncate font-semibold">{item.brand}</span>
            <PredictionBadge stationId={item.station_id} fuelType={item.fuel_type} />
            <FavoriteButton stationId={item.station_id} />
          </div>
          <p className="mt-0.5 truncate text-xs text-muted-foreground">
            {item.locality}, {item.province}
          </p>
          <p className="truncate text-xs text-muted-foreground/70">{item.address}</p>
        </div>

        {/* Price */}
        <div className="shrink-0 text-right">
          <p className="text-lg font-bold leading-none">{item.total_cost.toFixed(2)} €</p>
          <p className="mt-0.5 text-[11px] text-muted-foreground">total</p>
        </div>
      </div>

      {/* Stats row */}
      <div className="mt-2.5 grid grid-cols-3 gap-1 border-t pt-2.5 text-xs">
        <div>
          <p className="text-muted-foreground">Precio</p>
          <p className="font-medium">{item.price_per_liter.toFixed(3)} €/L</p>
        </div>
        <div>
          <p className="text-muted-foreground">Distancia</p>
          <p className="flex items-center gap-1 font-medium">
            <Car className="h-3 w-3 text-muted-foreground" aria-hidden />
            {formatDrivingSummary(item)}
          </p>
        </div>
        <div>
          <p className="text-muted-foreground">Desglose</p>
          <p className="font-medium">
            {item.fuel_cost.toFixed(2)}+{item.travel_cost.toFixed(2)} €
          </p>
        </div>
      </div>
    </div>
  );
});

// ── StationList ─────────────────────────────────────────────────────────────

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
      <div className="flex flex-col items-center gap-3 px-4 py-16 text-center">
        <span className="text-5xl">📍</span>
        <p className="font-medium">¿Dónde quieres repostar?</p>
        <p className="max-w-[240px] text-sm text-muted-foreground">
          Pulsa el icono de ubicación en la barra de búsqueda o escribe tu ciudad.
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-3 p-4">
        <RecommendationSkeleton />
        <RecommendationSkeleton />
        <RecommendationSkeleton />
        <RecommendationSkeleton />
      </div>
    );
  }

  if (isError) {
    return (
      <p className="px-4 py-6 text-sm text-destructive">
        Error al obtener resultados. Comprueba que el backend está disponible.
      </p>
    );
  }

  if (!items || items.length === 0) {
    return (
      <p className="px-4 py-6 text-sm text-muted-foreground">
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
        <div className="flex flex-col">
          <p className="text-sm text-muted-foreground">
            {items.length} gasolinera{items.length !== 1 ? "s" : ""}
          </p>
          {hasDrivingDistances && (
            <p className="text-[11px] text-muted-foreground/70">
              Distancias calculadas por carretera
            </p>
          )}
        </div>
        {hasFavorites && (
          <button
            type="button"
            onClick={() => setShowOnlyFavorites((p) => !p)}
            aria-pressed={showOnlyFavorites}
            className={cn(
              "flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium transition-colors",
              showOnlyFavorites
                ? "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                : "bg-muted text-muted-foreground hover:bg-muted/80",
            )}
          >
            <Heart className={cn("h-3 w-3", showOnlyFavorites && "fill-red-500")} />
            Favoritos
          </button>
        )}
      </div>

      {/* Scrollable list */}
      <div className="flex-1 space-y-2 overflow-y-auto p-4">
        {displayed.length === 0 ? (
          <p className="py-4 text-sm text-muted-foreground">
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
