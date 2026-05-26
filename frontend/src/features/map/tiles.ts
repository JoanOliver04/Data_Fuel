// Shared tile configuration for every Leaflet map in the app.
//
// The key is embedded in every tile request URL, so it reaches the browser. It
// must be a *separate*, domain-restricted TomTom key — never the backend
// routing secret (TOMTOM_API_KEY). See .env.example.
export const TOMTOM_TILE_KEY = import.meta.env.VITE_TOMTOM_TILE_KEY;

// Whether TomTom tiles (and the traffic overlay) are available. When false the
// app falls back to OpenStreetMap and hides the traffic toggle.
export const TOMTOM_TILES_ENABLED = Boolean(TOMTOM_TILE_KEY);
