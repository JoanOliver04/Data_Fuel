import { Loader2, MapPin } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface LocationPickerProps {
  lat: number | null;
  lon: number | null;
  onLocationChange: (lat: number, lon: number) => void;
}

export function LocationPicker({ lat, lon, onLocationChange }: LocationPickerProps) {
  const [loading, setLoading] = useState(false);
  const [geoError, setGeoError] = useState<string | null>(null);

  function detectLocation() {
    if (!navigator.geolocation) {
      setGeoError("Geolocalización no disponible en este navegador.");
      return;
    }
    setLoading(true);
    setGeoError(null);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        onLocationChange(
          Math.round(pos.coords.latitude * 1e6) / 1e6,
          Math.round(pos.coords.longitude * 1e6) / 1e6,
        );
        setLoading(false);
      },
      () => {
        setGeoError("No se pudo obtener la ubicación. Introduce las coordenadas manualmente.");
        setLoading(false);
      },
    );
  }

  return (
    <div className="space-y-3">
      <Button type="button" variant="outline" onClick={detectLocation} disabled={loading}>
        {loading ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <MapPin className="h-4 w-4" />
        )}
        {loading ? "Detectando…" : "Usar mi ubicación"}
      </Button>

      {geoError && <p className="text-sm text-destructive">{geoError}</p>}

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1">
          <Label htmlFor="lat">Latitud</Label>
          <Input
            id="lat"
            type="number"
            step="any"
            placeholder="39.4700"
            value={lat ?? ""}
            onChange={(e) => {
              const v = parseFloat(e.target.value);
              if (!isNaN(v)) onLocationChange(v, lon ?? 0);
            }}
          />
        </div>
        <div className="space-y-1">
          <Label htmlFor="lon">Longitud</Label>
          <Input
            id="lon"
            type="number"
            step="any"
            placeholder="-0.3760"
            value={lon ?? ""}
            onChange={(e) => {
              const v = parseFloat(e.target.value);
              if (!isNaN(v)) onLocationChange(lat ?? 0, v);
            }}
          />
        </div>
      </div>

      {lat !== null && lon !== null && (
        <p className="text-xs text-muted-foreground">
          {lat.toFixed(6)}, {lon.toFixed(6)}
        </p>
      )}
    </div>
  );
}
