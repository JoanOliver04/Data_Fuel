import { Moon, Search, Sun } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { FuelSelector } from "@/features/fuel-selector/FuelSelector";
import { HealthBadge } from "@/features/health/HealthBadge";
import { LocationPicker } from "@/features/location/LocationPicker";
import { useRecommendations } from "@/features/recommendations/hooks";
import { RecommendationList } from "@/features/recommendations/RecommendationList";
import { StationMap } from "@/features/recommendations/StationMap";
import type { RecommendationParams } from "@/features/recommendations/types";
import { useSettingsStore } from "@/stores/settings.store";

export function Home() {
  const { liters, kmCost, preferredFuel, userLat, userLon, theme, setLiters, setKmCost, setPreferredFuel, setLocation, setTheme } = useSettingsStore();

  const [maxDistance, setMaxDistance] = useState<number | undefined>(undefined);
  const [searchParams, setSearchParams] = useState<RecommendationParams | null>(null);

  const { data, isLoading, isError } = useRecommendations(searchParams);

  const canSearch = userLat !== null && userLon !== null;

  function handleSearch() {
    if (!canSearch) return;
    const params: RecommendationParams = {
      lat: userLat,
      lon: userLon,
      liters,
      fuel_type: preferredFuel,
      km_cost: kmCost,
      limit: 10,
    };
    if (maxDistance !== undefined) params.max_distance_km = maxDistance;
    setSearchParams(params);
  }

  return (
    <main className="container max-w-2xl space-y-6 py-8">
      <header>
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <h1 className="text-3xl font-bold tracking-tight">Data Fuel ⛽</h1>
            <p className="text-muted-foreground">
              Encuentra la gasolinera más rentable según precio y distancia.
            </p>
            <HealthBadge />
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            aria-label={theme === "dark" ? "Cambiar a modo claro" : "Cambiar a modo oscuro"}
          >
            {theme === "dark" ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
          </Button>
        </div>
      </header>

      <Card>
        <CardHeader className="pb-3">
          <h2 className="text-base font-semibold">📍 Mi ubicación</h2>
        </CardHeader>
        <CardContent>
          <LocationPicker lat={userLat} lon={userLon} onLocationChange={setLocation} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <h2 className="text-base font-semibold">🔍 Búsqueda</h2>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <Label htmlFor="liters">Litros a repostar</Label>
              <Input
                id="liters"
                type="number"
                min={1}
                max={200}
                step={1}
                value={liters}
                onChange={(e) => setLiters(Number(e.target.value))}
              />
            </div>
          </div>

          <div className="space-y-1">
            <Label>Combustible</Label>
            <FuelSelector value={preferredFuel} onChange={setPreferredFuel} className="pt-0.5" />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <Label htmlFor="kmcost">Coste por km (€/km)</Label>
              <Input
                id="kmcost"
                type="number"
                min={0}
                max={5}
                step={0.01}
                value={kmCost}
                onChange={(e) => setKmCost(Number(e.target.value))}
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="maxdist">Distancia máx. (km)</Label>
              <Input
                id="maxdist"
                type="number"
                min={0}
                step={1}
                placeholder="Sin límite"
                value={maxDistance ?? ""}
                onChange={(e) =>
                  setMaxDistance(e.target.value ? Number(e.target.value) : undefined)
                }
              />
            </div>
          </div>

          <Button className="w-full" onClick={handleSearch} disabled={!canSearch || isLoading}>
            <Search className="h-4 w-4" />
            {isLoading ? "Buscando…" : "Buscar gasolineras"}
          </Button>

          {!canSearch && (
            <p className="text-center text-xs text-muted-foreground">
              Introduce tu ubicación antes de buscar.
            </p>
          )}
        </CardContent>
      </Card>

      {data && data.length > 0 && userLat !== null && userLon !== null && (
        <Card>
          <CardHeader className="pb-3">
            <h2 className="text-base font-semibold">🗺 Mapa</h2>
          </CardHeader>
          <CardContent className="overflow-hidden rounded-b-lg p-0">
            <StationMap items={data} userLat={userLat} userLon={userLon} />
          </CardContent>
        </Card>
      )}

      <RecommendationList
        items={data}
        isLoading={isLoading}
        isError={isError}
        hasSearched={searchParams !== null}
      />
    </main>
  );
}
