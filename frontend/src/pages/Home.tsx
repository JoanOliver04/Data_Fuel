import { Calculator, Moon, Settings, Sun } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { AiAdviceCard } from "@/features/ai-recommendation/components/AiAdviceCard";
import { AiRecommendationButton } from "@/features/ai-recommendation/components/AiRecommendationButton";
import type { AiRecommendationResponse } from "@/features/ai-recommendation/types";
import { HealthBadge } from "@/features/health/HealthBadge";
import { MapView, type MapBBox } from "@/features/map/MapView";
import { InstallPrompt } from "@/features/pwa/InstallPrompt";
import { StandaloneBadge } from "@/features/pwa/StandaloneBadge";
import { SearchBar } from "@/features/search/SearchBar";
import { FiltersBar } from "@/features/search/FiltersBar";
import { useRecommendations } from "@/features/recommendations/hooks";
import { isStationOpenNow } from "@/features/recommendations/utils";
import { StationList } from "@/features/recommendations/StationList";
import type { RecommendationItem, RecommendationParams } from "@/features/recommendations/types";
import { SmartAdviceCard } from "@/features/smart-advice/SmartAdviceCard";
import type { SmartAdviceParams } from "@/features/smart-advice/types";
import { VehicleProfileBanner } from "@/features/vehicle-profile/VehicleProfileBanner";
import { useSettingsStore } from "@/stores/settings.store";
import { useSearchStore } from "@/stores/search.store";
import { cn } from "@/lib/utils";

// ── Mobile bottom sheet ─────────────────────────────────────────────────────

type SnapPoint = "peek" | "half" | "full";

const SNAP_PX: Record<SnapPoint, number> = {
  peek: 88,
  half: 0.45,
  full: 0.88,
};

interface BottomSheetProps {
  children: React.ReactNode;
}

function BottomSheet({ children }: BottomSheetProps) {
  const [snap, setSnap] = useState<SnapPoint>("half");
  const [dragging, setDragging] = useState(false);
  const [dragDelta, setDragDelta] = useState(0);
  const startYRef = useRef(0);
  const containerRef = useRef<HTMLDivElement>(null);

  function getSnapHeight(s: SnapPoint): number {
    const parent = containerRef.current?.parentElement?.clientHeight ?? window.innerHeight;
    if (s === "peek") return SNAP_PX.peek;
    if (s === "half") return Math.round(parent * SNAP_PX.half);
    return Math.round(parent * SNAP_PX.full);
  }

  function currentHeight(): number {
    return Math.max(SNAP_PX.peek, getSnapHeight(snap) + dragDelta);
  }

  function onTouchStart(e: React.TouchEvent) {
    startYRef.current = e.touches[0]?.clientY ?? 0;
    setDragging(true);
  }

  function onTouchMove(e: React.TouchEvent) {
    if (!dragging) return;
    const dy = (e.touches[0]?.clientY ?? 0) - startYRef.current;
    setDragDelta(-dy);
  }

  function onTouchEnd() {
    setDragging(false);
    const h = currentHeight();
    const parent = containerRef.current?.parentElement?.clientHeight ?? window.innerHeight;
    const peekH = SNAP_PX.peek;
    const halfH = Math.round(parent * SNAP_PX.half);
    const fullH = Math.round(parent * SNAP_PX.full);

    const distances = [
      { snap: "peek" as SnapPoint, d: Math.abs(h - peekH) },
      { snap: "half" as SnapPoint, d: Math.abs(h - halfH) },
      { snap: "full" as SnapPoint, d: Math.abs(h - fullH) },
    ];
    const nearest = distances.reduce((a, b) => (a.d < b.d ? a : b));
    setSnap(nearest.snap);
    setDragDelta(0);
  }

  const height = currentHeight();

  return (
    <div
      ref={containerRef}
      className={cn(
        "absolute inset-x-0 bottom-0 z-30 flex flex-col overflow-hidden rounded-t-3xl",
        "border-t border-border bg-background shadow-2xl shadow-black/10 dark:shadow-black/40",
        !dragging && "transition-[height] duration-300 ease-out",
      )}
      style={{ height }}
    >
      {/* Drag handle */}
      <div
        className="flex cursor-grab items-center justify-center py-3 active:cursor-grabbing"
        onTouchStart={onTouchStart}
        onTouchMove={onTouchMove}
        onTouchEnd={onTouchEnd}
      >
        <div className="h-1 w-10 rounded-full bg-muted-foreground/20" />
      </div>

      <div className="flex-1 overflow-y-auto">{children}</div>
    </div>
  );
}

// ── Home ─────────────────────────────────────────────────────────────────────

export function Home() {
  const { liters, kmCost, preferredFuel, userLat, userLon, theme, setTheme, activeVehicleProfileId } =
    useSettingsStore();
  const {
    radius,
    sortBy,
    filterBrands,
    filterOpenNow,
    selectedStationId,
    hoveredStationId,
    setSelectedStationId,
    setHoveredStationId,
  } = useSearchStore();

  const [boundsBBox, setBoundsBBox] = useState<MapBBox | null>(null);
  const [aiResult, setAiResult] = useState<AiRecommendationResponse | null>(null);

  useEffect(() => {
    setBoundsBBox(null);
    setAiResult(null);
  }, [userLat, userLon]);

  const searchParams = useMemo<RecommendationParams | null>(() => {
    if (userLat === null || userLon === null) return null;
    const base: RecommendationParams = {
      lat: userLat,
      lon: userLon,
      liters,
      fuel_type: preferredFuel,
      limit: 25,
    };
    if (activeVehicleProfileId !== null) {
      base.vehicle_profile_id = activeVehicleProfileId;
    } else {
      base.km_cost = kmCost;
    }
    if (boundsBBox) {
      return { ...base, ...boundsBBox };
    }
    if (radius !== undefined) base.max_distance_km = radius;
    return base;
  }, [userLat, userLon, liters, preferredFuel, kmCost, activeVehicleProfileId, radius, boundsBBox]);

  const { data, isLoading, isError } = useRecommendations(searchParams);

  const smartAdviceParams = useMemo<SmartAdviceParams | null>(() => {
    if (userLat === null || userLon === null) return null;
    return {
      lat: userLat,
      lon: userLon,
      fuel_type: preferredFuel,
      liters,
      km_cost: kmCost,
    };
  }, [userLat, userLon, preferredFuel, liters, kmCost]);

  const hasVehicleProfile = activeVehicleProfileId !== null;

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
      items = items.filter((item) => isStationOpenNow(item.schedule));
    }

    items.sort((a, b) => {
      if (sortBy === "price") return a.price_per_liter - b.price_per_liter;
      if (sortBy === "distance") return a.distance_km - b.distance_km;
      return a.total_cost - b.total_cost;
    });

    return items;
  }, [data, filterBrands, filterOpenNow, sortBy]);

  const aiStation = processedData?.[0] ?? null;

  const handleSearchArea = useCallback((bbox: MapBBox) => {
    setBoundsBBox(bbox);
  }, []);

  const hasSearched = searchParams !== null;
  const displayedItems = processedData ?? [];

  return (
    <div className="flex h-dvh flex-col bg-background">
      {/* ── Header ──────────────────────────────────────────────────────────── */}
      <header className="z-40 shrink-0 border-b border-border bg-background/90 backdrop-blur-xl supports-[backdrop-filter]:bg-background/80">
        <div className="mx-auto max-w-screen-xl space-y-2.5 px-4 pb-3 pt-3">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <div className="flex items-center gap-2">
                <span className="text-xl leading-none">⛽</span>
                <h1 className="text-lg font-extrabold tracking-tight">
                  Data <span className="text-primary">Fuel</span>
                </h1>
              </div>
              <HealthBadge />
              <StandaloneBadge />
            </div>
            <div className="flex items-center gap-0.5">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
                aria-label={theme === "dark" ? "Cambiar a modo claro" : "Cambiar a modo oscuro"}
                className="h-8 w-8 rounded-lg text-muted-foreground hover:text-foreground"
              >
                {theme === "dark" ? (
                  <Sun className="h-4 w-4" />
                ) : (
                  <Moon className="h-4 w-4" />
                )}
              </Button>
              <Link to="/simulator">
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label="Simulador de costes"
                  className="h-8 w-8 rounded-lg text-muted-foreground hover:text-foreground"
                >
                  <Calculator className="h-4 w-4" />
                </Button>
              </Link>
              <Link to="/settings">
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label="Ajustes"
                  className="h-8 w-8 rounded-lg text-muted-foreground hover:text-foreground"
                >
                  <Settings className="h-4 w-4" />
                </Button>
              </Link>
            </div>
          </div>
          <SearchBar isSearching={isLoading} />
          <FiltersBar allBrands={allBrands} />
        </div>
      </header>

      {/* ── Content ─────────────────────────────────────────────────────────── */}
      <div className="relative flex flex-1 overflow-hidden">
        {/* Desktop sidebar */}
        <aside className="hidden w-[380px] shrink-0 flex-col overflow-hidden border-r border-border bg-background lg:flex">
          {userLat !== null && userLon !== null ? (
            <>
              <div className="shrink-0 px-4 pt-4">
                <SmartAdviceCard params={smartAdviceParams} />
              </div>
              {aiStation && (
                <div className="shrink-0 px-4 pt-2">
                  <AiRecommendationButton
                    municipio={aiStation.municipality}
                    precioActual={aiStation.price_per_liter}
                    onResult={setAiResult}
                  />
                </div>
              )}
              {aiResult && (
                <div className="shrink-0 px-4 pt-2">
                  <AiAdviceCard response={aiResult} onDismiss={() => setAiResult(null)} />
                </div>
              )}
              {!hasVehicleProfile && (
                <div className="shrink-0 px-4 pt-2">
                  <VehicleProfileBanner />
                </div>
              )}
              <StationList
                items={processedData}
                isLoading={isLoading}
                isError={isError}
                hasSearched={hasSearched}
                selectedStationId={selectedStationId}
                onStationSelect={setSelectedStationId}
                onStationHover={setHoveredStationId}
              />
            </>
          ) : (
            <div className="flex flex-col items-center gap-4 px-6 py-20 text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-muted text-4xl">
                📍
              </div>
              <div>
                <p className="font-semibold">¿Dónde quieres repostar?</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  Usa la barra de búsqueda o activa la geolocalización.
                </p>
              </div>
            </div>
          )}
        </aside>

        {/* Map */}
        <div className="relative flex-1">
          {userLat !== null && userLon !== null ? (
            <MapView
              items={displayedItems}
              userLat={userLat}
              userLon={userLon}
              {...(radius !== undefined ? { radiusKm: radius } : {})}
              fuel={preferredFuel}
              selectedStationId={selectedStationId}
              hoveredStationId={hoveredStationId}
              isLoading={isLoading}
              onStationSelect={setSelectedStationId}
              onSearchArea={handleSearchArea}
              className="h-full w-full"
            />
          ) : (
            <div className="flex h-full flex-col items-center justify-center gap-5 px-6 text-center">
              <div className="flex h-24 w-24 items-center justify-center rounded-3xl bg-primary/10 text-5xl">
                ⛽
              </div>
              <div>
                <p className="text-2xl font-extrabold tracking-tight">
                  Data<span className="text-primary">Fuel</span>
                </p>
                <p className="mt-2 max-w-xs text-sm text-muted-foreground">
                  Activa la geolocalización o escribe tu ciudad para encontrar las mejores
                  gasolineras cercanas.
                </p>
              </div>
            </div>
          )}

          {/* Mobile bottom sheet */}
          <div className="lg:hidden">
            <BottomSheet>
              {smartAdviceParams && (
                <div className="px-4 pt-3">
                  <SmartAdviceCard params={smartAdviceParams} />
                </div>
              )}
              {aiStation && (
                <div className="px-4 pt-2">
                  <AiRecommendationButton
                    municipio={aiStation.municipality}
                    precioActual={aiStation.price_per_liter}
                    onResult={setAiResult}
                  />
                </div>
              )}
              {aiResult && (
                <div className="px-4 pt-2">
                  <AiAdviceCard response={aiResult} onDismiss={() => setAiResult(null)} />
                </div>
              )}
              {!hasVehicleProfile && (
                <div className="px-4 pt-2">
                  <VehicleProfileBanner />
                </div>
              )}
              <StationList
                items={processedData}
                isLoading={isLoading}
                isError={isError}
                hasSearched={hasSearched}
                selectedStationId={selectedStationId}
                onStationSelect={setSelectedStationId}
                onStationHover={setHoveredStationId}
              />
            </BottomSheet>
          </div>
        </div>
      </div>

      <InstallPrompt />
    </div>
  );
}
