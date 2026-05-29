import "leaflet/dist/leaflet.css";
import { divIcon, latLngBounds, type LatLngExpression } from "leaflet";
import { useEffect } from "react";
import { MapContainer, Marker, Popup, useMap } from "react-leaflet";

import { BaseTileLayer } from "@/features/map/components/BaseTileLayer";
import { makeMarkerIcon } from "@/features/map/components/StationMarker";

import type { RecommendationItem } from "./types";
import { formatDrivingSummary } from "./utils";

// Reuse the same pulsing dot as MapView for visual consistency.
const USER_LOCATION_ICON = divIcon({
  html: `<div class="df-user-location" role="img" aria-label="Tu ubicación"><span class="df-user-location__pulse"></span><span class="df-user-location__dot"></span></div>`,
  className: "",
  iconSize: [20, 20],
  iconAnchor: [10, 10],
  popupAnchor: [0, -14],
});

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
      <Marker position={userPos} icon={USER_LOCATION_ICON} keyboard={false}>
        <Popup>📍 Tu ubicación</Popup>
      </Marker>
      {items.map((item, i) => (
        <Marker
          key={item.station_id}
          position={[item.latitude, item.longitude]}
          icon={makeMarkerIcon(i + 1, "normal")}
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
