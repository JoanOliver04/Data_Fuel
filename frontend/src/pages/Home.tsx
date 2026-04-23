import { Search } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { HealthBadge } from "@/features/health/HealthBadge";
import { LocationPicker } from "@/features/location/LocationPicker";
import { useRecommendations } from "@/features/recommendations/hooks";
import { RecommendationList } from "@/features/recommendations/RecommendationList";
import type { RecommendationParams } from "@/features/recommendations/types";
import { useSettingsStore } from "@/stores/settings.store";
import { FUEL_LABELS, type FuelType } from "@/types/fuel";

export function Home() {
  const { liters, kmCost, preferredFuel, userLat, userLon, setLiters, setKmCost, setPreferredFuel, setLocation } =
    useSettingsStore();

  const [maxDistance, setMaxDistance] = useState<number | undefined>(undefined);
  const [searchParams, setSearchParams] = useState<RecommendationParams | null>(null);

  const { data, isLoading, isError } = useRecommendations(searchParams);

  const canSearch = userLat !== null && userLon !== null;

  function handleSearch() {
    if (!canSearch) return;
    setSearchParams({
      lat: userLat,
      lon: userLon,
      liters,
      fuel_type: preferredFuel,
      km_cost: kmCost,
      max_distance_km: maxDistance,
      limit: 10,
    });
  }

  return (
    <main className="container max-w-2xl space-y-6 py-8">
      <header className="space-y-1">
        <h1 className="text-3xl font-bold tracking-tight">Data Fuel ⛽</h1>
        <p className="text-muted-foreground">
          Encuentra la gasolinera más rentable según precio y distancia.
        </p>
        <HealthBadge />
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
            <div className="space-y-1">
              <Label htmlFor="fuel">Combustible</Label>
              <select
                id="fuel"
                value={preferredFuel}
                onChange={(e) => setPreferredFuel(e.target.value as FuelType)}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                {Object.entries(FUEL_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
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

      <RecommendationList
        items={data}
        isLoading={isLoading}
        isError={isError}
        hasSearched={searchParams !== null}
      />
    </main>
  );
}
