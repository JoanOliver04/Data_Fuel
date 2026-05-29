import "leaflet/dist/leaflet.css";

import { divIcon, type LatLngBounds } from "leaflet";
import { Flame, Loader2, MapPin, TrafficCone } from "lucide-react";
import { memo, useCallback, useEffect, useRef, useState, type CSSProperties } from "react";
import {
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
import { ClusteredStationMarkers } from "@/features/map/components/ClusteredStationMarkers";
import { MapStyleSelector } from "@/features/map/components/MapStyleSelector";
import { PinLocationControl } from "@/features/map/components/PinLocationControl";
import { PinLocationHint } from "@/features/map/components/PinLocationHint";
import { TrafficTileLayer } from "@/features/map/components/TrafficTileLayer";
import { UserSelectedMarker } from "@/features/map/components/UserSelectedMarker";
import { usePinLocationMode } from "@/features/map/hooks/usePinLocationMode";
import { TOMTOM_TILES_ENABLED, type MapStyle } from "@/features/map/tiles";
import type { RecommendationItem } from "@/features/recommendations/types";
import type { FuelType } from "@/types/fuel";

// Users who opt out of motion get instant map jumps instead of animated pans.
function reducedMotionDuration(normal: number): number {
  const reduce =
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  return reduce ? 0 : normal;
}

// ── User location marker ─────────────────────────────────────────────────────

// A pulsing blue dot rendered as a divIcon so the animation lives on an inner
// element and never fights Leaflet's positioning transform.
function makeUserLocationIcon() {
  return divIcon({
    html: `<div class="df-user-location" role="img" aria-label="Tu ubicación"><span class="df-user-location__pulse"></span><span class="df-user-location__dot"></span></div>`,
    className: "",
    iconSize: [20, 20],
    iconAnchor: [10, 10],
    popupAnchor: [0, -14],
  });
}

const USER_LOCATION_ICON = makeUserLocationIcon();

// ── Map event handlers ───────────────────────────────────────────────────────

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

interface PinClickHandlerProps {
  onPick: (lat: number, lon: number) => void;
}

function PinClickHandler({ onPick }: PinClickHandlerProps) {
  useMapEvents({
    click(e) {
      onPick(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
}

// ── Control button (shared visual pattern) ───────────────────────────────────

interface ControlButtonProps {
  onClick: () => void;
  active: boolean;
  ariaLabel: string;
  ariaPressed: boolean;
  children: React.ReactNode;
}

const ControlButton = memo(function ControlButton({
  onClick,
  active,
  ariaLabel,
  ariaPressed,
  children,
}: ControlButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={ariaPressed}
      aria-label={ariaLabel}
      className={cn(
        "flex min-h-[44px] min-w-[44px] items-center justify-center gap-1.5 rounded-xl px-3 py-2 text-xs font-medium shadow-elevation-lg ring-1 ring-border backdrop-blur-sm transition-all active:scale-95",
        active
          ? "bg-primary text-primary-foreground hover:bg-primary/90 shadow-primary/20"
          : "bg-background/95 text-foreground hover:bg-background",
      )}
    >
      {children}
    </button>
  );
});

// ── MapView ──────────────────────────────────────────────────────────────────

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
  radiusKm?: number;
  fuel?: FuelType;
  selectedStationId: number | null;
  hoveredStationId: number | null;
  isLoading: boolean;
  onStationSelect: (id: number | null) => void;
  onSearchArea: (bbox: MapBBox) => void;
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
  const [mapStyle, setMapStyle] = useState<MapStyle>("street");
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
        <BaseTileLayer style={mapStyle} />
        {trafficMode && <TrafficTileLayer />}

        <BoundsWatcher hasSearched={items.length > 0} onMapMoved={handleMapMoved} />
        <FlyToHandler lat={userLat} lon={userLon} />
        <FlyToStation items={items} selectedId={selectedStationId} />

        {pin.isActive && <PinClickHandler onPick={pin.placeAt} />}

        {/* User position dot OR the draggable pin — never both */}
        {pin.pinLocation ? (
          <UserSelectedMarker
            position={pin.pinLocation}
            draggable={pin.isActive}
            onDrag={pin.handleDrag}
            onDragEnd={pin.handleDragEnd}
          />
        ) : (
          <Marker position={userPos} icon={USER_LOCATION_ICON} zIndexOffset={900} keyboard={false}>
            <Popup>📍 Tu ubicación</Popup>
          </Marker>
        )}

        {/* Either clustered station markers OR the price heatmap */}
        {heatmapParams !== null ? (
          <HeatmapLayer params={heatmapParams} />
        ) : (
          <ClusteredStationMarkers
            items={items}
            selectedId={selectedStationId}
            hoveredId={hoveredStationId}
            onSelect={onStationSelect}
          />
        )}
      </MapContainer>

      {/* ── Left-side controls ──────────────────────────────────────────── */}

      {/* Map style selector — bottom-left, clear of Leaflet's zoom control */}
      <MapStyleSelector
        value={mapStyle}
        onChange={setMapStyle}
        className="absolute bottom-16 left-3 z-[500]"
      />

      {/* Pin-mode toggle — below the native zoom control (top-20 ≈ 80px) */}
      <PinLocationControl
        active={pin.isActive}
        onToggle={pin.toggle}
        className="absolute left-3 top-20 z-[500]"
      />

      {/* ── Top banners ─────────────────────────────────────────────────── */}

      {pin.isActive && (
        <div className="pointer-events-none absolute inset-x-0 top-4 z-[600] flex justify-center px-4">
          <PinLocationHint coords={pin.displayCoords} />
        </div>
      )}

      {pendingBounds && !isLoading && !pin.isActive && (
        <div className="pointer-events-none absolute inset-x-0 top-4 z-[500] flex justify-center">
          <button
            type="button"
            onClick={handleSearchArea}
            className={cn(
              "pointer-events-auto flex items-center gap-2 rounded-full px-4 py-2.5",
              "bg-background/95 text-sm font-medium shadow-elevation-lg ring-1 ring-border backdrop-blur-sm",
              "min-h-[44px] transition-all hover:bg-background hover:shadow-elevation-xl active:scale-95",
            )}
          >
            <MapPin className="h-4 w-4 text-primary" />
            Buscar en esta zona
          </button>
        </div>
      )}

      {/* ── Right-side controls ─────────────────────────────────────────── */}

      <div className="absolute right-3 top-3 z-[500] flex flex-col items-end gap-2">
        {radiusKm !== undefined && fuel !== undefined && (
          <ControlButton
            onClick={() => setHeatmapMode((p) => !p)}
            active={heatmapMode}
            ariaPressed={heatmapMode}
            ariaLabel="Mostrar mapa de calor de precios"
          >
            <Flame className="h-4 w-4" />
            <span className="hidden sm:inline">Heatmap</span>
          </ControlButton>
        )}

        {TOMTOM_TILES_ENABLED && (
          <ControlButton
            onClick={() => setTrafficMode((p) => !p)}
            active={trafficMode}
            ariaPressed={trafficMode}
            ariaLabel="Mostrar tráfico en vivo"
          >
            <TrafficCone className="h-4 w-4" />
            <span className="hidden sm:inline">Tráfico</span>
          </ControlButton>
        )}

        {isLoading && (
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-background/95 shadow-elevation-lg ring-1 ring-border">
            <Loader2 className="h-4 w-4 animate-spin text-primary" />
          </div>
        )}
      </div>

      {heatmapMode && <HeatmapLegend />}
    </div>
  );
}
