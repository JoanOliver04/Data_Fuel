import { divIcon, type DivIcon } from "leaflet";
import { memo } from "react";
import { Marker, Popup } from "react-leaflet";

import type { RecommendationItem } from "@/features/recommendations/types";

import { StationPopup } from "./StationPopup";

// ── Icon factory ─────────────────────────────────────────────────────────────

// Rank 1 = cheapest → green, rank 2 = middle → orange, rank 3 = expensive → red.
const RANK_BASE_COLORS = ["#22c55e", "#f97316", "#ef4444"];

type MarkerState = "normal" | "selected" | "hovered";

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
  savings?: number;
  onSelect: (id: number) => void;
}

export const StationMarker = memo(function StationMarker({
  item,
  rank,
  isSelected,
  isHovered,
  savings,
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
      <Popup
        className="df-popup"
        minWidth={272}
        maxWidth={272}
        autoPan
        autoPanPaddingTopLeft={[8, 8]}
        autoPanPaddingBottomRight={[8, 72]}
      >
        <StationPopup
          item={item}
          rank={rank}
          savings={savings}
          onViewDetails={() => onSelect(item.station_id)}
        />
      </Popup>
    </Marker>
  );
});
