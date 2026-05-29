import { TileLayer } from "react-leaflet";

import { MAP_STYLE_CONFIGS, type MapStyle } from "@/features/map/tiles";

interface BaseTileLayerProps {
  style?: MapStyle;
}

export function BaseTileLayer({ style = "street" }: BaseTileLayerProps) {
  const cfg = MAP_STYLE_CONFIGS[style];
  return (
    <TileLayer
      attribution={cfg.attribution}
      url={cfg.url}
      maxZoom={cfg.maxZoom}
      subdomains={cfg.subdomains ?? "abc"}
    />
  );
}
