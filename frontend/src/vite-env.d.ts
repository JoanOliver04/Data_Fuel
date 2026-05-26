/// <reference types="vite/client" />
/// <reference types="vite-plugin-pwa/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string;
  /** Client-side TomTom Maps tile key. Optional — falls back to OSM when unset. */
  readonly VITE_TOMTOM_TILE_KEY?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
