import "leaflet/dist/leaflet.css";

import { divIcon, type DivIcon, type LatLngBounds } from "leaflet";
import { Flame, Loader2, MapPin, TrafficCone } from "lucide-react";
import { memo, useCallback, useEffect, useRef, useState, type CSSProperties } from "react";
import {
  CircleMarker,
  MapContainer,
  Marker,
  Popup,
  useMap,
  useMapEvents,
} from "react-leaflet";

import { cn } from "@/lib/utils";
import { HeatmapLayer } from "@/features/heatmap/HeatmapLayer";
import { HeatmapLegend } from "@/features/heatmap/HeatmapLegend";
import type { HeatmapParams } from "@/features/heatmap/types";
import { BaseTileLayer } from "@/features/map/components/BaseTileLayer";
import { PinLocationControl } from "@/features/map/components/PinLocationControl";
import { PinLocationHint } from "@/features/map/components/PinLocationHint";
import { TrafficTileLayer } from "@/features/map/components/TrafficTileLayer";
import { UserSelectedMarker } from "@/features/map/components/UserSelectedMarker";
import { usePinLocationMode } from "@/features/map/hooks/usePinLocationMode";
import { TOMTOM_TILES_ENABLED } from "@/features/map/tiles";
import type { RecommendationItem } from "@/features/recommendations/types";
import { formatDrivingSummary } from "@/features/recommendations/utils";
import type { FuelType } from "@/types/fuel";

// Users who opt out of motion get instant map jumps instead of animated pans.
function reducedMotionDuration(normal: number): number {
  const reduce =
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  return reduce ? 0 : normal;
}

// ── Icon factory ────────────────────────────────────────────────────────────

const RANK_COLORS = ["#f59e0b", "#94a3b8", "#b45309"];

function makeMarkerIcon(rank: number, state: "normal" | "selected" | "hovered"): DivIcon {
  const base = RANK_COLORS[rank - 1] ?? "#3b82f6";
  const bg = state === "selected" ? "#f97316" : state === "hovered" ? "#818cf8" : base;
  const size = state === "selected" ? 36 : state === "hovered" ? 32 : 28;
  const border = state === "selected" ? 3 : 2;
  const shadow = state === "selected"
    ? "0 0 0 4px rgba(249,115,22,.35),0 2px 8px rgba(0,0,0,.4)"
    : "0 1px 4px rgba(0,0,0,.4)";

  return divIcon({
    html: `<div style="background:${bg};color:#fff;border-radius:50%;width:${size}px;height:${size}px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:${size === 36 ? 14 : 12}px;border:${border}px solid #fff;box-shadow:${shadow};transition:all .15s ease">${rank}</div>`,
    className: "",
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -(size / 2 + 4)],
  });
}

// ── Map event handler ───────────────────────────────────────────────────────

interface BoundsWatcherProps {
  hasSearched: boolean;
  onMapMoved: (bounds: LatLngBounds) => void;
}

function BoundsWatcher({ hasSearched, onMapMoved }: BoundsWatcherProps) {
  const initRef = useRef(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useMapEvents({
    moveend(e) {
      if (!hasSearched) return;
      // Skip the very first moveend (programmatic flyTo on load)
      if (!initRef.current) {
        initRef.current = true;
        return;
      }
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        onMapMoved(e.target.getBounds() as LatLngBounds);
      }, 400);
    },
  });

  return null;
}

// ── Fly to location ─────────────────────────────────────────────────────────

interface FlyToHandlerProps {
  lat: number;
  lon: number;
}

function FlyToHandler({ lat, lon }: FlyToHandlerProps) {
  const map = useMap();
  const prev = useRef<string>("");

  useEffect(() => {
    const key = `${lat},${lon}`;
    if (key !== prev.current) {
      prev.current = key;
      map.flyTo([lat, lon], Math.max(map.getZoom(), 13), { duration: reducedMotionDuration(1.2) });
    }
  }, [lat, lon, map]);

  return null;
}

// ── Fly to selected station ─────────────────────────────────────────────────

interface FlyToStationProps {
  items: RecommendationItem[];
  selectedId: number | null;
}

function FlyToStation({ items, selectedId }: FlyToStationProps) {
  const map = useMap();
  const prevId = useRef<number | null>(null);

  useEffect(() => {
    if (selectedId !== null && selectedId !== prevId.current) {
      const station = items.find((s) => s.station_id === selectedId);
      if (station) {
        map.flyTo([station.latitude, station.longitude], Math.max(map.getZoom(), 14), {
          duration: reducedMotionDuration(0.8),
        });
      }
    }
    prevId.current = selectedId;
  }, [selectedId, items, map]);

  return null;
}

// ── Pin-mode click capture ───────────────────────────────────────────────────

interface PinClickHandlerProps {
  onPick: (lat: number, lon: number) => void;
}

// Mounted only while pin mode is active, so the click listener exists for
// exactly as long as it's needed (react-leaflet detaches it on unmount). Clicks
// on existing markers don't propagate to the map, so they never drop a pin.
function PinClickHandler({ onPick }: PinClickHandlerProps) {
  useMapEvents({
    click(e) {
      onPick(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
}

// ── Station marker ──────────────────────────────────────────────────────────

interface StationMarkerProps {
  item: RecommendationItem;
  rank: number;
  isSelected: boolean;
  isHovered: boolean;
  onSelect: (id: number) => void;
}

const StationMarker = memo(function StationMarker({
  item,
  rank,
  isSelected,
  isHovered,
  onSelect,
}: StationMarkerProps) {
  const state = isSelected ? "selected" : isHovered ? "hovered" : "normal";
  const icon = makeMarkerIcon(rank, state);

  return (
    <Marker
      position={[item.latitude, item.longitude]}
      icon={icon}
      eventHandlers={{
        click: () => onSelect(item.station_id),
      }}
      zIndexOffset={isSelected ? 1000 : isHovered ? 500 : 0}
    >
      <Popup minWidth={200}>
        <div className="space-y-1 p-1 text-sm">
          <p className="font-semibold">{item.brand}</p>
          <p className="text-xs text-gray-500">
            {item.locality}, {item.province}
          </p>
          <p className="text-xs text-gray-400">{item.address}</p>
          <div className="mt-2 grid grid-cols-2 gap-x-3 gap-y-0.5 border-t pt-2 text-xs">
            <span className="text-gray-500">Precio:</span>
            <span className="font-medium">{item.price_per_liter.toFixed(3)} €/L</span>
            <span className="text-gray-500">Distancia:</span>
            <span className="font-medium">{formatDrivingSummary(item)}</span>
            <span className="text-gray-500">Coste real:</span>
            <span className="font-bold text-orange-600">{item.total_cost.toFixed(2)} €</span>
          </div>
        </div>
      </Popup>
    </Marker>
  );
});

// ── MapView ─────────────────────────────────────────────────────────────────

export interface MapBBox {
  north: number;
  south: number;
  east: number;
  west: number;
}

interface MapViewProps {
  items: RecommendationItem[];
  userLat: number;
  userLon: number;
  /** Search radius in km — required to enable the price heatmap layer. */
  radiusKm?: number;
  /** Fuel type — required to enable the price heatmap layer. */
  fuel?: FuelType;
  selectedStationId: number | null;
  hoveredStationId: number | null;
  isLoading: boolean;
  onStationSelect: (id: number | null) => void;
  onSearchArea: (bbox: MapBBox) => void;
  /** Bottom padding in px — used on mobile to push Leaflet controls above the peek sheet. */
  paddingBottom?: number;
  className?: string;
}

export function MapView({
  items,
  userLat,
  userLon,
  radiusKm,
  fuel,
  selectedStationId,
  hoveredStationId,
  isLoading,
  onStationSelect,
  onSearchArea,
  paddingBottom,
  className,
}: MapViewProps) {
  const [pendingBounds, setPendingBounds] = useState<LatLngBounds | null>(null);
  const [heatmapMode, setHeatmapMode] = useState(false);
  const [trafficMode, setTrafficMode] = useState(false);
  const pin = usePinLocationMode();
  const userPos: [number, number] = [userLat, userLon];

  const heatmapParams: HeatmapParams | null =
    heatmapMode && radiusKm !== undefined && fuel !== undefined
      ? { lat: userLat, lon: userLon, radius_km: radiusKm, fuel }
      : null;

  const handleMapMoved = useCallback((bounds: LatLngBounds) => {
    setPendingBounds(bounds);
  }, []);

  function handleSearchArea() {
    if (!pendingBounds) return;
    onSearchArea({
      north: pendingBounds.getNorth(),
      south: pendingBounds.getSouth(),
      east: pendingBounds.getEast(),
      west: pendingBounds.getWest(),
    });
    setPendingBounds(null);
  }

  return (
    <div
      className={cn(
        "relative h-full w-full",
        pin.isActive && "[&_.leaflet-container]:cursor-crosshair",
        className,
      )}
      style={paddingBottom !== undefined ? { "--lf-bottom": `${paddingBottom}px` } as CSSProperties : undefined}
    >
      <MapContainer
        center={userPos}
        zoom={13}
        className="h-full w-full"
        scrollWheelZoom
        zoomControl
      >
        <BaseTileLayer />
        {trafficMode && <TrafficTileLayer />}

        <BoundsWatcher hasSearched={items.length > 0} onMapMoved={handleMapMoved} />
        <FlyToHandler lat={userLat} lon={userLon} />
        <FlyToStation items={items} selectedId={selectedStationId} />

        {/* Capture clicks as pin placements only while pin mode is on. */}
        {pin.isActive && <PinClickHandler onPick={pin.placeAt} />}

        {/* User position — the draggable pin replaces the plain dot once the
            user has manually placed one, so there's never a duplicate marker. */}
        {pin.pinLocation ? (
          <UserSelectedMarker
            position={pin.pinLocation}
            draggable={pin.isActive}
            onDrag={pin.handleDrag}
            onDragEnd={pin.handleDragEnd}
          />
        ) : (
          <CircleMarker
            center={userPos}
            radius={10}
            pathOptions={{
              color: "#2563eb",
              fillColor: "#3b82f6",
              fillOpacity: 0.85,
              weight: 2,
            }}
          >
            <Popup>📍 Tu ubicación</Popup>
          </CircleMarker>
        )}

        {/* Either station markers OR the price heatmap — never both, so the
            map stays readable. */}
        {heatmapParams !== null ? (
          <HeatmapLayer params={heatmapParams} />
        ) : (
          items.map((item, i) => (
            <StationMarker
              key={item.station_id}
              item={item}
              rank={i + 1}
              isSelected={selectedStationId === item.station_id}
              isHovered={hoveredStationId === item.station_id}
              onSelect={onStationSelect}
            />
          ))
        )}
      </MapContainer>

      {/* Pin-mode toggle — tucked under the zoom control on the left. */}
      <PinLocationControl
        active={pin.isActive}
        onToggle={pin.toggle}
        className="absolute left-3 top-20 z-[500]"
      />

      {/* Helper banner + live coordinates while placing/dragging the pin. */}
      {pin.isActive && (
        <div className="pointer-events-none absolute inset-x-0 top-4 z-[600] flex justify-center px-4">
          <PinLocationHint coords={pin.displayCoords} />
        </div>
      )}

      {/* "Search this area" overlay — hidden in pin mode, where panning to a
          pinned point shouldn't masquerade as an area search. */}
      {pendingBounds && !isLoading && !pin.isActive && (
        <div className="pointer-events-none absolute inset-x-0 top-4 z-[500] flex justify-center">
          <button
            type="button"
            onClick={handleSearchArea}
            className={cn(
              "pointer-events-auto flex items-center gap-2 rounded-full px-4 py-2",
              "bg-background/95 text-sm font-medium shadow-lg ring-1 ring-border backdrop-blur-sm",
              "transition-all hover:bg-background hover:shadow-xl active:scale-95",
            )}
          >
            <MapPin className="h-4 w-4 text-primary" />
            Buscar en esta zona
          </button>
        </div>
      )}

      {/* Layer toggles + status — a single top-right stack. Items flow in
          source order, so the spinner sits below whatever toggles are present
          with no manual offset math. */}
      <div className="absolute right-3 top-3 z-[500] flex flex-col items-end gap-2">
        {/* Heatmap toggle — only when the parent supplied radius + fuel. */}
        {radiusKm !== undefined && fuel !== undefined && (
          <button
            type="button"
            onClick={() => setHeatmapMode((p) => !p)}
            aria-pressed={heatmapMode}
            aria-label="Mostrar mapa de calor de precios"
            className={cn(
              "flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium shadow-md ring-1 ring-border backdrop-blur-sm transition-colors",
              heatmapMode
                ? "bg-primary text-primary-foreground hover:bg-primary/90"
                : "bg-background/95 text-foreground hover:bg-background",
            )}
          >
            <Flame className="h-3.5 w-3.5" />
            Heatmap
          </button>
        )}

        {/* Live-traffic toggle — only when TomTom tiles are configured, since
            the overlay reuses the same key. */}
        {TOMTOM_TILES_ENABLED && (
          <button
            type="button"
            onClick={() => setTrafficMode((p) => !p)}
            aria-pressed={trafficMode}
            aria-label="Mostrar tráfico en vivo"
            className={cn(
              "flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium shadow-md ring-1 ring-border backdrop-blur-sm transition-colors",
              trafficMode
                ? "bg-primary text-primary-foreground hover:bg-primary/90"
                : "bg-background/95 text-foreground hover:bg-background",
            )}
          >
            <TrafficCone className="h-3.5 w-3.5" />
            Tráfico
          </button>
        )}

        {isLoading && (
          <div className="rounded-full bg-background/90 p-2 shadow-md">
            <Loader2 className="h-4 w-4 animate-spin text-primary" />
          </div>
        )}
      </div>

      {/* Heatmap legend — bottom-left, paired with the toggle so the colour
          meaning is self-explanatory whenever the layer is on. */}
      {heatmapMode && <HeatmapLegend />}
    </div>
  );
}
