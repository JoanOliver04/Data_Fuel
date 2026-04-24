import "leaflet/dist/leaflet.css";

import { divIcon, type DivIcon, type LatLngBounds } from "leaflet";
import { Loader2, MapPin } from "lucide-react";
import { memo, useCallback, useEffect, useRef, useState } from "react";
import {
  CircleMarker,
  MapContainer,
  Marker,
  Popup,
  TileLayer,
  useMap,
  useMapEvents,
} from "react-leaflet";

import { cn } from "@/lib/utils";
import type { RecommendationItem } from "@/features/recommendations/types";

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
      map.flyTo([lat, lon], Math.max(map.getZoom(), 13), { duration: 1.2 });
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
          duration: 0.8,
        });
      }
    }
    prevId.current = selectedId;
  }, [selectedId, items, map]);

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
            <span className="font-medium">{item.distance_km.toFixed(1)} km</span>
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
  selectedStationId: number | null;
  hoveredStationId: number | null;
  isLoading: boolean;
  onStationSelect: (id: number | null) => void;
  onSearchArea: (bbox: MapBBox) => void;
  className?: string;
}

export function MapView({
  items,
  userLat,
  userLon,
  selectedStationId,
  hoveredStationId,
  isLoading,
  onStationSelect,
  onSearchArea,
  className,
}: MapViewProps) {
  const [pendingBounds, setPendingBounds] = useState<LatLngBounds | null>(null);
  const userPos: [number, number] = [userLat, userLon];

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
    <div className={cn("relative h-full w-full", className)}>
      <MapContainer
        center={userPos}
        zoom={13}
        className="h-full w-full"
        scrollWheelZoom
        zoomControl
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <BoundsWatcher hasSearched={items.length > 0} onMapMoved={handleMapMoved} />
        <FlyToHandler lat={userLat} lon={userLon} />
        <FlyToStation items={items} selectedId={selectedStationId} />

        {/* User position */}
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

        {/* Station markers */}
        {items.map((item, i) => (
          <StationMarker
            key={item.station_id}
            item={item}
            rank={i + 1}
            isSelected={selectedStationId === item.station_id}
            isHovered={hoveredStationId === item.station_id}
            onSelect={onStationSelect}
          />
        ))}
      </MapContainer>

      {/* "Search this area" overlay */}
      {pendingBounds && !isLoading && (
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

      {/* Loading indicator */}
      {isLoading && (
        <div className="absolute right-3 top-3 z-[500] rounded-full bg-background/90 p-2 shadow-md">
          <Loader2 className="h-4 w-4 animate-spin text-primary" />
        </div>
      )}
    </div>
  );
}
