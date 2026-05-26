import { TileLayer } from "react-leaflet";

import { TOMTOM_TILE_KEY } from "@/features/map/tiles";

// TomTom raster basemap. Fast CDN + richer road/POI detail than the OSM public
// tile server — which is also disallowed for production traffic, so it stays a
// dev-only fallback when no key is set.
const TOMTOM_URL =
  `https://api.tomtom.com/map/1/tile/basic/main/{z}/{x}/{y}.png?key=${TOMTOM_TILE_KEY}`;
const TOMTOM_ATTRIBUTION =
  '&copy; <a href="https://www.tomtom.com">TomTom</a>';

const OSM_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
const OSM_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';

/**
 * Shared basemap layer for every Leaflet map in the app. Uses TomTom tiles when
 * VITE_TOMTOM_TILE_KEY is configured, otherwise degrades to OpenStreetMap so
 * local dev still renders without a key.
 */
export function BaseTileLayer() {
  if (TOMTOM_TILE_KEY) {
    return <TileLayer attribution={TOMTOM_ATTRIBUTION} url={TOMTOM_URL} maxZoom={22} />;
  }
  return <TileLayer attribution={OSM_ATTRIBUTION} url={OSM_URL} />;
}
