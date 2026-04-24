import { useState } from "react";

import { Heart } from "lucide-react";

import { useSettingsStore } from "@/stores/settings.store";

import type { RecommendationItem } from "./types";
import { RecommendationCard } from "./RecommendationCard";
import { RecommendationSkeleton } from "./RecommendationSkeleton";

interface RecommendationListProps {
  items: RecommendationItem[] | undefined;
  isLoading: boolean;
  isError: boolean;
  hasSearched: boolean;
}

export function RecommendationList({
  items,
  isLoading,
  isError,
  hasSearched,
}: RecommendationListProps) {
  const favorites = useSettingsStore((s) => s.favorites);
  const [showOnlyFavorites, setShowOnlyFavorites] = useState(false);

  if (!hasSearched) return null;

  if (isLoading) {
    return (
      <div className="space-y-3">
        <RecommendationSkeleton />
        <RecommendationSkeleton />
        <RecommendationSkeleton />
      </div>
    );
  }

  if (isError) {
    return (
      <p className="py-4 text-sm text-destructive">
        Error al obtener resultados. Comprueba que el backend está disponible.
      </p>
    );
  }

  if (!items || items.length === 0) {
    return (
      <p className="py-4 text-sm text-muted-foreground">
        No se encontraron gasolineras con los filtros indicados.
      </p>
    );
  }

  const hasFavorites = items.some((item) => favorites.includes(item.station_id));
  const displayed = showOnlyFavorites
    ? items.filter((item) => favorites.includes(item.station_id))
    : items;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {items.length} gasolinera{items.length !== 1 ? "s" : ""} encontrada
          {items.length !== 1 ? "s" : ""}
        </p>
        {hasFavorites && (
          <button
            type="button"
            onClick={() => setShowOnlyFavorites((prev) => !prev)}
            aria-pressed={showOnlyFavorites}
            className={`flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              showOnlyFavorites
                ? "bg-red-100 text-red-700"
                : "bg-muted text-muted-foreground hover:bg-muted/80"
            }`}
          >
            <Heart className={`h-3 w-3 ${showOnlyFavorites ? "fill-red-500" : ""}`} />
            Favoritos
          </button>
        )}
      </div>

      {displayed.length === 0 ? (
        <p className="py-4 text-sm text-muted-foreground">
          Ninguna gasolinera favorita en los resultados.
        </p>
      ) : (
        displayed.map((item, i) => (
          <RecommendationCard key={item.station_id} item={item} rank={i + 1} />
        ))
      )}
    </div>
  );
}
