import { TileLayer } from "react-leaflet";

import { TOMTOM_TILE_KEY } from "@/features/map/tiles";

// TomTom Traffic Flow overlay — a transparent raster layer drawn over the
// basemap. The "relative" style colours roads by current speed vs free-flow
// (green = clear → red = congested), so a route to a cheap station shows real
// driving conditions. zIndex keeps it above the basemap but below the marker
// pane, so station pins stay clickable on top.
const TRAFFIC_URL =
  `https://api.tomtom.com/traffic/map/4/tile/flow/relative/{z}/{x}/{y}.png?key=${TOMTOM_TILE_KEY}`;

/**
 * Live traffic overlay. Render conditionally on top of {@link BaseTileLayer};
 * only meaningful when TomTom tiles are enabled (it shares the same key).
 */
export function TrafficTileLayer() {
  return <TileLayer url={TRAFFIC_URL} maxZoom={22} opacity={0.85} zIndex={400} />;
}
