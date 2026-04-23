import { Loader2 } from "lucide-react";

import type { RecommendationItem } from "./types";
import { RecommendationCard } from "./RecommendationCard";

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
  if (!hasSearched) return null;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center gap-2 py-12 text-muted-foreground">
        <Loader2 className="h-5 w-5 animate-spin" />
        <span>Buscando gasolineras…</span>
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

  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">
        {items.length} gasolinera{items.length !== 1 ? "s" : ""} encontrada
        {items.length !== 1 ? "s" : ""}
      </p>
      {items.map((item, i) => (
        <RecommendationCard key={item.station_id} item={item} rank={i + 1} />
      ))}
    </div>
  );
}
