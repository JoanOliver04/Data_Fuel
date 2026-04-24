import { Moon, Sun } from "lucide-react";
import { useMemo } from "react";

import { Button } from "@/components/ui/button";
import { HealthBadge } from "@/features/health/HealthBadge";
import { SearchBar } from "@/features/search/SearchBar";
import { FiltersBar } from "@/features/search/FiltersBar";
import { useRecommendations } from "@/features/recommendations/hooks";
import { RecommendationList } from "@/features/recommendations/RecommendationList";
import { StationMap } from "@/features/recommendations/StationMap";
import type { RecommendationParams, RecommendationItem } from "@/features/recommendations/types";
import { useSettingsStore } from "@/stores/settings.store";
import { useSearchStore } from "@/stores/search.store";

function stationIsOpen(schedule: string): boolean {
  if (!schedule) return true;
  const s = schedule.toUpperCase();
  return s.includes("24H") || s.includes("L-D: 24");
}

export function Home() {
  const { liters, kmCost, preferredFuel, userLat, userLon, theme, setTheme } = useSettingsStore();
  const { radius, sortBy, filterBrands, filterOpenNow } = useSearchStore();

  const searchParams = useMemo<RecommendationParams | null>(() => {
    if (userLat === null || userLon === null) return null;
    const params: RecommendationParams = {
      lat: userLat,
      lon: userLon,
      liters,
      fuel_type: preferredFuel,
      km_cost: kmCost,
      limit: 25,
    };
    if (radius !== undefined) params.max_distance_km = radius;
    return params;
  }, [userLat, userLon, liters, preferredFuel, kmCost, radius]);

  const { data, isLoading, isError } = useRecommendations(searchParams);

  const allBrands = useMemo<string[]>(() => {
    if (!data) return [];
    return [...new Set(data.map((item) => item.brand))].sort();
  }, [data]);

  const processedData = useMemo<RecommendationItem[] | undefined>(() => {
    if (!data) return undefined;
    let items = [...data];

    if (filterBrands.length > 0) {
      items = items.filter((item) => filterBrands.includes(item.brand));
    }
    if (filterOpenNow) {
      items = items.filter((item) => stationIsOpen(item.schedule));
    }

    items.sort((a, b) => {
      if (sortBy === "price") return a.price_per_liter - b.price_per_liter;
      if (sortBy === "distance") return a.distance_km - b.distance_km;
      return a.total_cost - b.total_cost;
    });

    return items;
  }, [data, filterBrands, filterOpenNow, sortBy]);

  return (
    <div className="min-h-dvh bg-muted/20">
      {/* Sticky header */}
      <header className="sticky top-0 z-40 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
        <div className="mx-auto max-w-4xl space-y-2.5 px-4 pb-3 pt-3">
          {/* Brand row */}
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <h1 className="text-lg font-bold tracking-tight">Data Fuel ⛽</h1>
              <HealthBadge />
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              aria-label={theme === "dark" ? "Cambiar a modo claro" : "Cambiar a modo oscuro"}
            >
              {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </Button>
          </div>

          {/* Search bar */}
          <SearchBar isSearching={isLoading} />

          {/* Filter bar */}
          <FiltersBar allBrands={allBrands} />
        </div>
      </header>

      {/* Results */}
      <main className="mx-auto max-w-4xl space-y-4 px-4 py-4">
        {/* Map */}
        {processedData && processedData.length > 0 && userLat !== null && userLon !== null && (
          <div className="overflow-hidden rounded-2xl border border-border shadow-sm">
            <StationMap items={processedData} userLat={userLat} userLon={userLon} />
          </div>
        )}

        {/* Station list */}
        <RecommendationList
          items={processedData}
          isLoading={isLoading}
          isError={isError}
          hasSearched={searchParams !== null}
        />

        {/* Empty state when no location set */}
        {searchParams === null && (
          <div className="flex flex-col items-center gap-3 py-16 text-center">
            <span className="text-5xl">📍</span>
            <p className="text-base font-medium">¿Dónde quieres repostar?</p>
            <p className="max-w-xs text-sm text-muted-foreground">
              Pulsa el icono de ubicación en la barra de búsqueda o escribe tu ciudad para
              encontrar las mejores gasolineras.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
