import { divIcon, type DivIcon } from "leaflet";
import { memo } from "react";
import { Marker, Popup } from "react-leaflet";

import type { RecommendationItem } from "@/features/recommendations/types";
import { formatDrivingSummary } from "@/features/recommendations/utils";

// ── Icon factory ─────────────────────────────────────────────────────────────

// Rank 1 = cheapest → green, rank 2 = middle → orange, rank 3 = expensive → red.
// These map to the same hues used in the price heatmap (priceColor.ts), giving
// the map a single coherent colour language.
const RANK_BASE_COLORS = ["#22c55e", "#f97316", "#ef4444"];

type MarkerState = "normal" | "selected" | "hovered";

// Module-level cache: avoid creating identical DivIcon objects on every render.
const iconCache = new Map<string, DivIcon>();

export function makeMarkerIcon(rank: number, state: MarkerState): DivIcon {
  const key = `${rank}:${state}`;
  const cached = iconCache.get(key);
  if (cached) return cached;

  const base = RANK_BASE_COLORS[rank - 1] ?? "#3b82f6";
  const bg = state === "selected" ? "#f97316" : state === "hovered" ? "#818cf8" : base;
  const size = state === "selected" ? 36 : state === "hovered" ? 32 : 28;
  const border = state === "selected" ? 3 : 2;
  const shadow =
    state === "selected"
      ? "0 0 0 4px rgba(249,115,22,.35),0 2px 8px rgba(0,0,0,.45)"
      : state === "hovered"
        ? "0 0 0 3px rgba(129,140,248,.4),0 2px 6px rgba(0,0,0,.35)"
        : "0 2px 6px rgba(0,0,0,.35),0 1px 2px rgba(0,0,0,.2)";

  const icon = divIcon({
    html: `<div style="background:${bg};color:#fff;border-radius:50%;width:${size}px;height:${size}px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:${size >= 36 ? 14 : 12}px;border:${border}px solid rgba(255,255,255,0.95);box-shadow:${shadow};transition:all .15s ease;letter-spacing:-0.02em">${rank}</div>`,
    className: "",
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -(size / 2 + 4)],
  });

  iconCache.set(key, icon);
  return icon;
}

// ── Component ─────────────────────────────────────────────────────────────────

interface StationMarkerProps {
  item: RecommendationItem;
  rank: number;
  isSelected: boolean;
  isHovered: boolean;
  onSelect: (id: number) => void;
}

export const StationMarker = memo(function StationMarker({
  item,
  rank,
  isSelected,
  isHovered,
  onSelect,
}: StationMarkerProps) {
  const state: MarkerState = isSelected ? "selected" : isHovered ? "hovered" : "normal";
  const icon = makeMarkerIcon(rank, state);

  return (
    <Marker
      position={[item.latitude, item.longitude]}
      icon={icon}
      eventHandlers={{ click: () => onSelect(item.station_id) }}
      zIndexOffset={isSelected ? 1000 : isHovered ? 500 : 0}
    >
      <Popup minWidth={200} className="df-popup">
        <div className="space-y-1 p-1 text-sm">
          <div className="flex items-center gap-2">
            <span
              className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold text-white"
              style={{ background: RANK_BASE_COLORS[rank - 1] ?? "#3b82f6" }}
            >
              {rank}
            </span>
            <p className="font-semibold leading-tight">{item.brand}</p>
          </div>
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
