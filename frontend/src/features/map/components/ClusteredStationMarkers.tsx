import { divIcon } from "leaflet";
import MarkerClusterGroup from "react-leaflet-cluster";

import type { RecommendationItem } from "@/features/recommendations/types";

import { StationMarker } from "./StationMarker";

// ── Cluster icon factory ─────────────────────────────────────────────────────

function makeClusterIcon(count: number) {
  const size = count >= 50 ? 52 : count >= 10 ? 44 : 36;
  const fontSize = count >= 50 ? 15 : count >= 10 ? 13 : 12;

  return divIcon({
    html: `<div class="df-cluster" style="width:${size}px;height:${size}px;font-size:${fontSize}px">${count}</div>`,
    className: "",
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

// ── Component ────────────────────────────────────────────────────────────────

interface ClusteredStationMarkersProps {
  items: RecommendationItem[];
  selectedId: number | null;
  hoveredId: number | null;
  onSelect: (id: number) => void;
}

export function ClusteredStationMarkers({
  items,
  selectedId,
  hoveredId,
  onSelect,
}: ClusteredStationMarkersProps) {
  return (
    <MarkerClusterGroup
      iconCreateFunction={makeClusterIcon}
      maxClusterRadius={60}
      spiderfyOnMaxZoom
      showCoverageOnHover={false}
      zoomToBoundsOnClick
      animate
      chunkedLoading
    >
      {items.map((item, i) => (
        <StationMarker
          key={item.station_id}
          item={item}
          rank={i + 1}
          isSelected={selectedId === item.station_id}
          isHovered={hoveredId === item.station_id}
          onSelect={onSelect}
        />
      ))}
    </MarkerClusterGroup>
  );
}
