import { Moon, Sun } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { HealthBadge } from "@/features/health/HealthBadge";
import { MapView, type MapBBox } from "@/features/map/MapView";
import { SearchBar } from "@/features/search/SearchBar";
import { FiltersBar } from "@/features/search/FiltersBar";
import { useRecommendations } from "@/features/recommendations/hooks";
import { StationList } from "@/features/recommendations/StationList";
import type { RecommendationItem, RecommendationParams } from "@/features/recommendations/types";
import { SmartAdviceCard } from "@/features/smart-advice/SmartAdviceCard";
import type { SmartAdviceParams } from "@/features/smart-advice/types";
import { useSettingsStore } from "@/stores/settings.store";
import { useSearchStore } from "@/stores/search.store";
import { cn } from "@/lib/utils";

// ── Mobile bottom sheet ─────────────────────────────────────────────────────

type SnapPoint = "peek" | "half" | "full";

const SNAP_PX: Record<SnapPoint, number> = {
  peek: 88,
  half: 0.45,   // fraction of parent height
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
    setDragDelta(-dy); // drag up = positive height
  }

  function onTouchEnd() {
    setDragging(false);
    const h = currentHeight();
    const parent = containerRef.current?.parentElement?.clientHeight ?? window.innerHeight;
    const peekH = SNAP_PX.peek;
    const halfH = Math.round(parent * SNAP_PX.half);
    const fullH = Math.round(parent * SNAP_PX.full);

    // Snap to nearest point
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
        "border-t border-border bg-background shadow-2xl",
        !dragging && "transition-[height] duration-300 ease-out",
      )}
      style={{ height }}
    >
      {/* Drag handle */}
      <div
        className="flex cursor-grab items-center justify-center py-2.5 active:cursor-grabbing"
        onTouchStart={onTouchStart}
        onTouchMove={onTouchMove}
        onTouchEnd={onTouchEnd}
      >
        <div className="h-1 w-10 rounded-full bg-muted-foreground/30" />
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">{children}</div>
    </div>
  );
}

// ── stationIsOpen ───────────────────────────────────────────────────────────

function stationIsOpen(schedule: string): boolean {
  if (!schedule) return true;
  const s = schedule.toUpperCase();
  return s.includes("24H") || s.includes("L-D: 24");
}

// ── Home ────────────────────────────────────────────────────────────────────

export function Home() {
  const { liters, kmCost, preferredFuel, userLat, userLon, theme, setTheme } = useSettingsStore();
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

  // Bounding box from "Search in area" — overrides radius when set
  const [boundsBBox, setBoundsBBox] = useState<MapBBox | null>(null);

  // Reset bbox when the user picks a new location
  useEffect(() => {
    setBoundsBBox(null);
  }, [userLat, userLon]);

  const searchParams = useMemo<RecommendationParams | null>(() => {
    if (userLat === null || userLon === null) return null;
    const base: RecommendationParams = {
      lat: userLat,
      lon: userLon,
      liters,
      fuel_type: preferredFuel,
      km_cost: kmCost,
      limit: 25,
    };
    if (boundsBBox) {
      return { ...base, ...boundsBBox };
    }
    if (radius !== undefined) base.max_distance_km = radius;
    return base;
  }, [userLat, userLon, liters, preferredFuel, kmCost, radius, boundsBBox]);

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

  // Unique brands for FiltersModal
  const allBrands = useMemo<string[]>(() => {
    if (!data) return [];
    return [...new Set(data.map((item) => item.brand))].sort();
  }, [data]);

  // Client-side filter + sort
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

  const handleSearchArea = useCallback((bbox: MapBBox) => {
    setBoundsBBox(bbox);
  }, []);

  const hasSearched = searchParams !== null;
  const displayedItems = processedData ?? [];

  return (
    <div className="flex h-dvh flex-col bg-background">
      {/* ── Sticky header ─────────────────────────────────────────────────── */}
      <header className="z-40 shrink-0 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
        <div className="mx-auto max-w-screen-xl space-y-2.5 px-4 pb-3 pt-3">
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
          <SearchBar isSearching={isLoading} />
          <FiltersBar allBrands={allBrands} />
        </div>
      </header>

      {/* ── Content area ──────────────────────────────────────────────────── */}
      <div className="relative flex flex-1 overflow-hidden">
        {/* ── Desktop: station list sidebar (left) ──────────────────────── */}
        <aside className="hidden w-[380px] shrink-0 flex-col overflow-hidden border-r border-border lg:flex">
          {userLat !== null && userLon !== null ? (
            <>
              <div className="shrink-0 px-4 pt-4">
                <SmartAdviceCard params={smartAdviceParams} />
              </div>
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
            <div className="flex flex-col items-center gap-3 px-6 py-16 text-center">
              <span className="text-5xl">📍</span>
              <p className="font-medium">¿Dónde quieres repostar?</p>
              <p className="text-sm text-muted-foreground">
                Usa la barra de búsqueda o activa la geolocalización.
              </p>
            </div>
          )}
        </aside>

        {/* ── Map (full width on mobile, flex-1 on desktop) ─────────────── */}
        <div className="relative flex-1">
          {userLat !== null && userLon !== null ? (
            <MapView
              items={displayedItems}
              userLat={userLat}
              userLon={userLon}
              selectedStationId={selectedStationId}
              hoveredStationId={hoveredStationId}
              isLoading={isLoading}
              onStationSelect={setSelectedStationId}
              onSearchArea={handleSearchArea}
              className="h-full w-full"
            />
          ) : (
            /* No location: full-screen prompt */
            <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
              <span className="text-7xl">⛽</span>
              <p className="text-xl font-bold">Data Fuel</p>
              <p className="max-w-xs text-sm text-muted-foreground">
                Activa la geolocalización o escribe tu ciudad para encontrar las mejores
                gasolineras cercanas.
              </p>
            </div>
          )}

          {/* ── Mobile bottom sheet (overlays map) ──────────────────────── */}
          <div className="lg:hidden">
            <BottomSheet>
              {smartAdviceParams && (
                <div className="px-4 pt-3">
                  <SmartAdviceCard params={smartAdviceParams} />
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
    </div>
  );
}
