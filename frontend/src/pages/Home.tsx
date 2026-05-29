import { Calculator, Moon, Settings, Sun } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { AiAdviceCard } from "@/features/ai-recommendation/components/AiAdviceCard";
import { AiRecommendationButton } from "@/features/ai-recommendation/components/AiRecommendationButton";
import type { AiRecommendationResponse } from "@/features/ai-recommendation/types";
import { AiExplainabilityCard } from "@/features/xai/components/AiExplainabilityCard";
import type { ExplainRecommendationRequest } from "@/features/xai/types";
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
import { OptimizationProfileSelector } from "@/features/optimization/OptimizationProfileSelector";
import { OptimizationInsightCard } from "@/features/optimization/OptimizationInsightCard";
import { ComparisonCenter } from "@/features/comparison";
import { FuelStrategyCard } from "@/features/fuel-strategy";
import type { SmartAdviceParams } from "@/features/smart-advice/types";
import { VehicleProfileBanner } from "@/features/vehicle-profile/VehicleProfileBanner";
import { useSettingsStore } from "@/stores/settings.store";
import { useSearchStore } from "@/stores/search.store";
import { useUiStore, type SnapPoint } from "@/stores/ui.store";
import { cn } from "@/lib/utils";

// ── Mobile bottom sheet ─────────────────────────────────────────────────────

const SNAP_PX: Record<SnapPoint, number> = {
  peek: 88,
  half: 0.45,
  full: 0.88,
};

// Height of the fixed bottom nav bar (matches h-14 = 56px).
const NAV_HEIGHT = 56;

interface BottomSheetProps {
  children: React.ReactNode;
  snap: SnapPoint;
  onSnapChange: (s: SnapPoint) => void;
}

function BottomSheet({ children, snap, onSnapChange }: BottomSheetProps) {
  const [dragging, setDragging] = useState(false);
  const startYRef = useRef(0);
  const startTimeRef = useRef(0);
  const containerRef = useRef<HTMLDivElement>(null);
  // Drag state lives in refs so a gesture never re-renders the page behind the
  // sheet — height is written straight to the DOM, one rAF-batched write/frame.
  const draggingRef = useRef(false);
  const heightRef = useRef(0);
  const pendingYRef = useRef(0);
  const rafRef = useRef<number | null>(null);

  function getSnapHeight(s: SnapPoint): number {
    const parent = containerRef.current?.parentElement?.clientHeight ?? window.innerHeight;
    // Leave at least 20px gap above the sheet so it never clips the header.
    const maxH = parent - NAV_HEIGHT - 20;
    if (s === "peek") return SNAP_PX.peek;
    if (s === "half") return Math.min(Math.round(parent * SNAP_PX.half), maxH);
    return Math.min(Math.round(parent * SNAP_PX.full), maxH);
  }

  function maxHeight(): number {
    const parent = containerRef.current?.parentElement?.clientHeight ?? window.innerHeight;
    return parent - NAV_HEIGHT - 20;
  }

  function applyDragFrame() {
    rafRef.current = null;
    if (!draggingRef.current || !containerRef.current) return;
    const dy = pendingYRef.current - startYRef.current; // up = negative dy = taller
    const h = Math.min(maxHeight(), Math.max(SNAP_PX.peek, getSnapHeight(snap) - dy));
    heightRef.current = h;
    containerRef.current.style.height = `${h}px`;
  }

  function onTouchStart(e: React.TouchEvent) {
    startYRef.current = e.touches[0]?.clientY ?? 0;
    startTimeRef.current = Date.now();
    heightRef.current = getSnapHeight(snap);
    draggingRef.current = true;
    setDragging(true); // one render to drop the height transition for the drag
  }

  function onTouchMove(e: React.TouchEvent) {
    if (!draggingRef.current) return;
    pendingYRef.current = e.touches[0]?.clientY ?? 0;
    if (rafRef.current == null) rafRef.current = requestAnimationFrame(applyDragFrame);
  }

  function onTouchEnd(e: React.TouchEvent) {
    if (!draggingRef.current) return;
    draggingRef.current = false;
    if (rafRef.current != null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
    // Re-render restores the transition; React reclaims style.height → it
    // animates smoothly from the dragged height to the chosen snap.
    setDragging(false);

    const endY = e.changedTouches[0]?.clientY ?? startYRef.current;
    const elapsed = Date.now() - startTimeRef.current;
    // positive = finger moved up = sheet grew taller
    const velocity = elapsed > 0 ? (startYRef.current - endY) / elapsed : 0;

    const FLICK_VEL = 0.5; // px/ms (500 px/s)

    let target: SnapPoint;
    if (velocity > FLICK_VEL) {
      target = "full";
    } else if (velocity < -FLICK_VEL) {
      target = "peek";
    } else {
      const h = heightRef.current;
      const distances = [
        { snap: "peek" as SnapPoint, d: Math.abs(h - SNAP_PX.peek) },
        { snap: "half" as SnapPoint, d: Math.abs(h - getSnapHeight("half")) },
        { snap: "full" as SnapPoint, d: Math.abs(h - getSnapHeight("full")) },
      ];
      target = distances.reduce((a, b) => (a.d < b.d ? a : b)).snap;
    }
    onSnapChange(target);
  }

  useEffect(() => {
    return () => {
      if (rafRef.current != null) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  const height = getSnapHeight(snap);

  return (
    <div
      ref={containerRef}
      className={cn(
        "absolute inset-x-0 z-30 flex flex-col overflow-hidden rounded-t-3xl",
        "border-t border-border bg-background shadow-elevation-xl",
        !dragging && "transition-[height] duration-300 ease-out",
      )}
      style={{ height, bottom: NAV_HEIGHT, willChange: dragging ? "height" : undefined }}
    >
      {/* Drag handle */}
      <div
        className="flex cursor-grab touch-none items-center justify-center py-3.5 active:cursor-grabbing"
        onTouchStart={onTouchStart}
        onTouchMove={onTouchMove}
        onTouchEnd={onTouchEnd}
      >
        <div className="h-1 w-10 rounded-full bg-muted-foreground/25" />
      </div>

      <div className="flex-1 overflow-y-auto overflow-x-hidden overscroll-contain scroll-smooth">
        {children}
      </div>
    </div>
  );
}

// ── Home ─────────────────────────────────────────────────────────────────────

export function Home() {
  const {
    liters,
    kmCost,
    preferredFuel,
    userLat,
    userLon,
    theme,
    setTheme,
    activeVehicleProfileId,
    optimizationProfile,
  } = useSettingsStore();
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
  const snap = useUiStore((s) => s.snap);
  const setSnap = useUiStore((s) => s.setSnap);

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
      optimization_profile: optimizationProfile,
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
  }, [userLat, userLon, liters, preferredFuel, kmCost, activeVehicleProfileId, radius, boundsBBox, optimizationProfile]);

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
      // Default: honour the backend's multi-objective ranking when a profile
      // populated optimization_score; otherwise fall back to total cost.
      const aKey = a.optimization_score ?? a.total_cost;
      const bKey = b.optimization_score ?? b.total_cost;
      return aKey - bKey;
    });

    return items;
  }, [data, filterBrands, filterOpenNow, sortBy]);

  const aiStation = processedData?.[0] ?? null;

  // Params for the XAI explanation, derived from the same station + settings the
  // recommendation used. Non-null only once a recommendation has been fetched,
  // so the explain endpoint fires exactly once per "Recomendación IA" click.
  const xaiParams = useMemo<ExplainRecommendationRequest | null>(() => {
    if (aiResult === null || aiStation === null || userLat === null || userLon === null) {
      return null;
    }
    return {
      lat: userLat,
      lon: userLon,
      fuel_type: preferredFuel,
      municipio: aiStation.municipality,
      station_lat: aiStation.latitude,
      station_lon: aiStation.longitude,
      precio_actual: aiStation.price_per_liter,
    };
  }, [aiResult, aiStation, userLat, userLon, preferredFuel]);

  const handleSearchArea = useCallback((bbox: MapBBox) => {
    setBoundsBBox(bbox);
  }, []);

  // When user taps a station on the map, snap the sheet up so they can see it.
  const handleStationSelect = useCallback(
    (id: number | null) => {
      setSelectedStationId(id);
      if (id !== null && useUiStore.getState().snap === "peek") setSnap("half");
    },
    [setSelectedStationId, setSnap],
  );

  const hasSearched = searchParams !== null;
  const displayedItems = processedData ?? [];

  const sheetContent = (
    <>
      {smartAdviceParams && (
        <div className="px-4 pt-3">
          <FuelStrategyCard params={smartAdviceParams} items={processedData} />
        </div>
      )}
      <div className="px-4 pt-2.5">
        <OptimizationProfileSelector />
      </div>
      <div className="px-4 pt-2">
        <OptimizationInsightCard items={processedData} />
      </div>
      {aiStation && (
        <div className="px-4 pt-2">
          <AiRecommendationButton
            municipio={aiStation.municipality}
            stationLat={aiStation.latitude}
            stationLon={aiStation.longitude}
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
      {xaiParams && (
        <div className="px-4 pt-2">
          <AiExplainabilityCard params={xaiParams} />
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
    </>
  );

  return (
    <div className="flex h-dvh flex-col overflow-hidden bg-background">
      {/* ── Header ──────────────────────────────────────────────────────────── */}
      <header className="z-40 shrink-0 border-b border-border bg-background/90 backdrop-blur-xl supports-[backdrop-filter]:bg-background/80">
        <div className="mx-auto max-w-screen-xl space-y-2.5 px-4 pb-3 pt-3">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-2.5">
              <div className="flex shrink-0 items-center gap-2">
                <span className="text-xl leading-none">⛽</span>
                <h1 className="text-lg font-extrabold tracking-tight">
                  Data <span className="text-primary">Fuel</span>
                </h1>
              </div>
              <HealthBadge />
              <StandaloneBadge />
            </div>
            <div className="flex shrink-0 items-center gap-0.5">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
                aria-label={theme === "dark" ? "Cambiar a modo claro" : "Cambiar a modo oscuro"}
                className="h-9 w-9 rounded-lg text-muted-foreground hover:text-foreground"
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
                  className="h-9 w-9 rounded-lg text-muted-foreground hover:text-foreground"
                >
                  <Calculator className="h-4 w-4" />
                </Button>
              </Link>
              <Link to="/settings">
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label="Ajustes"
                  className="h-9 w-9 rounded-lg text-muted-foreground hover:text-foreground"
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
        {/* Desktop sidebar — independent, single vertical scroll container */}
        <aside className="hidden w-[380px] shrink-0 flex-col overflow-y-auto overflow-x-hidden scroll-smooth border-r border-border bg-background lg:flex">
          {userLat !== null && userLon !== null ? (
            <>
              <div className="shrink-0 px-4 pt-4">
                <FuelStrategyCard params={smartAdviceParams} items={processedData} />
              </div>
              <div className="shrink-0 px-4 pt-2">
                <OptimizationProfileSelector />
              </div>
              <div className="shrink-0 px-4 pt-2">
                <OptimizationInsightCard items={processedData} />
              </div>
              {aiStation && (
                <div className="shrink-0 px-4 pt-2">
                  <AiRecommendationButton
                    municipio={aiStation.municipality}
                    stationLat={aiStation.latitude}
                    stationLon={aiStation.longitude}
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
              {xaiParams && (
                <div className="shrink-0 px-4 pt-2">
                  <AiExplainabilityCard params={xaiParams} />
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
              onStationSelect={handleStationSelect}
              onSearchArea={handleSearchArea}
              paddingBottom={NAV_HEIGHT + SNAP_PX.peek}
              className="h-full w-full"
            />
          ) : (
            <div className="flex h-full flex-col items-center justify-center gap-5 px-6 pb-16 text-center lg:pb-0">
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

          {/* Mobile bottom sheet — controlled by snap state from Home */}
          <div className="lg:hidden">
            <BottomSheet snap={snap} onSnapChange={setSnap}>
              {sheetContent}
            </BottomSheet>
          </div>
        </div>
      </div>

      <ComparisonCenter items={processedData} />

      <InstallPrompt />
    </div>
  );
}
