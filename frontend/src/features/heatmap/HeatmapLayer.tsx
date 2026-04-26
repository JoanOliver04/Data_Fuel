import { CircleMarker, Tooltip } from "react-leaflet";

import { useHeatmap } from "./hooks";
import { priceColor } from "./priceColor";
import type { HeatmapParams } from "./types";

interface HeatmapLayerProps {
  params: HeatmapParams;
}

export function HeatmapLayer({ params }: HeatmapLayerProps) {
  const { data } = useHeatmap(params);
  if (!data) return null;

  return (
    <>
      {data.features.map((f) => {
        const [lon, lat] = f.geometry.coordinates;
        const { id, price, price_normalized, brand, name } = f.properties;
        const color = priceColor(price_normalized);
        const label =
          name && name !== brand ? `${brand} · ${name}` : brand;
        return (
          <CircleMarker
            key={id}
            center={[lat, lon]}
            // Pixel radius is intentional (not metres): the heatmap is meant
            // to read at any zoom, like a UI marker rather than a geo-buffer.
            radius={18}
            pathOptions={{
              color,
              fillColor: color,
              fillOpacity: 0.7,
              weight: 0,
            }}
          >
            <Tooltip direction="top" offset={[0, -8]} opacity={1} sticky>
              <span className="text-xs font-medium">
                {label} · {price.toFixed(3)} €/L
              </span>
            </Tooltip>
          </CircleMarker>
        );
      })}
    </>
  );
}
