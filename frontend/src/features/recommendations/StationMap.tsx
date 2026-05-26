import "leaflet/dist/leaflet.css";
import { divIcon, latLngBounds, type DivIcon, type LatLngExpression } from "leaflet";
import { useEffect } from "react";
import { CircleMarker, MapContainer, Marker, Popup, useMap } from "react-leaflet";

import { BaseTileLayer } from "@/features/map/components/BaseTileLayer";

import type { RecommendationItem } from "./types";
import { formatDrivingSummary } from "./utils";

const RANK_BG = ["#f59e0b", "#94a3b8", "#b45309"];

function makeIcon(rank: number): DivIcon {
  const bg = RANK_BG[rank - 1] ?? "#3b82f6";
  return divIcon({
    html: `<div style="background:${bg};color:#fff;border-radius:50%;width:28px;height:28px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:12px;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.4)">${rank}</div>`,
    className: "",
    iconSize: [28, 28],
    iconAnchor: [14, 14],
    popupAnchor: [0, -14],
  });
}

type Pos = [number, number];

function FitBounds({ positions }: { positions: Pos[] }) {
  const map = useMap();
  useEffect(() => {
    if (positions.length === 0) return;
    map.fitBounds(latLngBounds(positions as LatLngExpression[]), { padding: [40, 40] });
  }, [map, positions]);
  return null;
}

interface StationMapProps {
  items: RecommendationItem[];
  userLat: number;
  userLon: number;
}

export function StationMap({ items, userLat, userLon }: StationMapProps) {
  const userPos: Pos = [userLat, userLon];
  const allPositions: Pos[] = [userPos, ...items.map((s): Pos => [s.latitude, s.longitude])];

  return (
    <MapContainer
      center={userPos}
      zoom={13}
      className="h-72 w-full rounded-lg"
      scrollWheelZoom={false}
    >
      <BaseTileLayer />
      <FitBounds positions={allPositions} />
      <CircleMarker
        center={userPos}
        radius={10}
        pathOptions={{ color: "#2563eb", fillColor: "#3b82f6", fillOpacity: 0.85, weight: 2 }}
      >
        <Popup>📍 Tu ubicación</Popup>
      </CircleMarker>
      {items.map((item, i) => (
        <Marker
          key={item.station_id}
          position={[item.latitude, item.longitude]}
          icon={makeIcon(i + 1)}
        >
          <Popup>
            <div style={{ minWidth: 160 }}>
              <p style={{ fontWeight: 600, marginBottom: 2 }}>{item.brand}</p>
              <p style={{ fontSize: 12, color: "#6b7280", marginBottom: 6 }}>{item.address}</p>
              <p style={{ fontSize: 13 }}>
                <span style={{ color: "#6b7280" }}>Total: </span>
                <strong>{Number(item.total_cost).toFixed(2)} €</strong>
              </p>
              <p style={{ fontSize: 13 }}>
                <span style={{ color: "#6b7280" }}>Precio: </span>
                {Number(item.price_per_liter).toFixed(3)} €/L
              </p>
              <p style={{ fontSize: 13 }}>
                <span style={{ color: "#6b7280" }}>Distancia: </span>
                {formatDrivingSummary(item)}
              </p>
            </div>
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}
