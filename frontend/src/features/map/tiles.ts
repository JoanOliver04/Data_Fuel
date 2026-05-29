// Shared tile configuration for every Leaflet map in the app.
//
// The key is embedded in every tile request URL, so it reaches the browser. It
// must be a *separate*, domain-restricted TomTom key — never the backend
// routing secret (TOMTOM_API_KEY). See .env.example.
export const TOMTOM_TILE_KEY = import.meta.env.VITE_TOMTOM_TILE_KEY;

// Whether TomTom tiles (and the traffic overlay) are available. When false the
// app falls back to OpenStreetMap and hides the traffic toggle.
export const TOMTOM_TILES_ENABLED = Boolean(TOMTOM_TILE_KEY);

// ── Map style definitions ────────────────────────────────────────────────────

export type MapStyle = "street" | "dark" | "satellite";

interface TileConfig {
  url: string;
  attribution: string;
  maxZoom: number;
  /** Subdomains for load-balanced tile servers (default: "abc"). */
  subdomains?: string;
}

const TOMTOM_ATTR = '&copy; <a href="https://www.tomtom.com">TomTom</a>';
const OSM_ATTR = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';
const CARTO_ATTR = `${OSM_ATTR} &copy; <a href="https://carto.com/attributions">CARTO</a>`;
const ESRI_ATTR = 'Tiles &copy; <a href="https://www.esri.com">Esri</a> &mdash; Source: Esri, USGS, AeroGRID, IGN, and the GIS User Community';

export const MAP_STYLE_CONFIGS: Record<MapStyle, TileConfig> = {
  street: TOMTOM_TILE_KEY
    ? {
        url: `https://api.tomtom.com/map/1/tile/basic/main/{z}/{x}/{y}.png?key=${TOMTOM_TILE_KEY}`,
        attribution: TOMTOM_ATTR,
        maxZoom: 22,
      }
    : {
        url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        attribution: OSM_ATTR,
        maxZoom: 19,
        subdomains: "abc",
      },

  dark: {
    url: "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    attribution: CARTO_ATTR,
    maxZoom: 19,
    subdomains: "abcd",
  },

  satellite: {
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attribution: ESRI_ATTR,
    maxZoom: 19,
  },
};

export const MAP_STYLE_LABELS: Record<MapStyle, string> = {
  street: "Mapa",
  dark: "Oscuro",
  satellite: "Satélite",
};
