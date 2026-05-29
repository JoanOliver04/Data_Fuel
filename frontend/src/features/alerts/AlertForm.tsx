import { ChevronLeft, Plus } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { FUEL_LABELS, type FuelType } from "@/types/fuel";
import { useSettingsStore } from "@/stores/settings.store";

import { useCreateAlert } from "./hooks";
import { ALERT_REGISTRY, TONE_CLASSES, type AlertCategory, type AlertTypeMeta } from "./registry";
import type { AlertCreate, AlertType } from "./types";

// ── Smart Fuel Alerts — create flow ──────────────────────────────────────────
// Two steps: pick a watch type (grouped by category), then fill the few inputs
// that type needs (driven entirely by the registry's `fields`). Location, fuel
// and liters are prefilled from the user's settings so most alerts are one tap
// away. Geo-dependent types are gated when no location is set.

const CATEGORY_LABEL: Record<AlertCategory, string> = {
  price: "Precio",
  ai: "Predicción IA",
  digest: "Resúmenes",
};

const CREATABLE = Object.values(ALERT_REGISTRY).filter((m) => m.creatable);

function groupByCategory(): [AlertCategory, AlertTypeMeta[]][] {
  const order: AlertCategory[] = ["price", "ai", "digest"];
  return order
    .map((cat) => [cat, CREATABLE.filter((m) => m.category === cat)] as [AlertCategory, AlertTypeMeta[]])
    .filter(([, items]) => items.length > 0);
}

interface AlertFormProps {
  userId: string;
  /** Called after a successful create — lets the center jump back to the list. */
  onCreated: () => void;
}

export function AlertForm({ userId, onCreated }: AlertFormProps) {
  const { preferredFuel, userLat, userLon, liters } = useSettingsStore();
  const create = useCreateAlert(userId);

  const [type, setType] = useState<AlertType | null>(null);
  const [fuel, setFuel] = useState<FuelType>(preferredFuel);
  const [thresholdPrice, setThresholdPrice] = useState("");
  const [thresholdPct, setThresholdPct] = useState("");
  const [brand, setBrand] = useState("");

  const meta = type !== null ? ALERT_REGISTRY[type] : null;
  const hasLocation = userLat !== null && userLon !== null;
  const geoMissing = meta?.needsGeo === true && !hasLocation;

  function reset() {
    setType(null);
    setThresholdPrice("");
    setThresholdPct("");
    setBrand("");
    setFuel(preferredFuel);
  }

  function canSubmit(): boolean {
    if (meta === null || geoMissing) return false;
    if (meta.fields.includes("threshold_price") && !(Number(thresholdPrice) > 0)) return false;
    if (meta.fields.includes("threshold_pct") && !(Number(thresholdPct) > 0)) return false;
    if (meta.fields.includes("brand") && brand.trim().length === 0) return false;
    return true;
  }

  function handleSubmit() {
    if (meta === null || !canSubmit()) return;
    const body: AlertCreate = { user_identifier: userId, alert_type: meta.type, fuel_type: fuel };
    if (meta.needsGeo && hasLocation) {
      body.latitude = userLat;
      body.longitude = userLon;
      body.liters = liters;
    }
    if (meta.fields.includes("threshold_price")) body.threshold_price = Number(thresholdPrice);
    if (meta.fields.includes("threshold_pct")) body.threshold_pct = Number(thresholdPct);
    if (meta.fields.includes("brand")) body.brand = brand.trim();

    create.mutate(body, {
      onSuccess: () => {
        reset();
        onCreated();
      },
    });
  }

  // ── Step 1: pick a type ────────────────────────────────────────────────────
  if (meta === null) {
    return (
      <div className="space-y-4">
        {groupByCategory().map(([cat, items]) => (
          <div key={cat}>
            <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              {CATEGORY_LABEL[cat]}
            </p>
            <div className="space-y-1.5">
              {items.map((m) => {
                const tone = TONE_CLASSES[m.tone];
                const Icon = m.icon;
                return (
                  <button
                    key={m.type}
                    type="button"
                    onClick={() => setType(m.type)}
                    className="flex w-full items-center gap-3 rounded-xl border border-border bg-card px-3 py-2.5 text-left transition-colors hover:bg-muted/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    <span className={cn("flex h-9 w-9 shrink-0 items-center justify-center rounded-lg", tone.chip)}>
                      <Icon className={cn("h-4 w-4", tone.icon)} aria-hidden />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-sm font-semibold text-foreground">{m.label}</span>
                      <span className="block text-xs leading-snug text-muted-foreground">
                        {m.description}
                      </span>
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    );
  }

  // ── Step 2: configure ──────────────────────────────────────────────────────
  return (
    <div className="space-y-4">
      <button
        type="button"
        onClick={reset}
        className="-ml-1 inline-flex items-center gap-1 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
      >
        <ChevronLeft className="h-4 w-4" />
        Cambiar tipo
      </button>

      <div className="rounded-xl bg-muted/50 px-3 py-2.5">
        <p className="text-sm font-semibold text-foreground">{meta.label}</p>
        <p className="text-xs text-muted-foreground">{meta.description}</p>
      </div>

      {/* Fuel */}
      <div className="space-y-1.5">
        <Label htmlFor="alert-fuel">Combustible</Label>
        <select
          id="alert-fuel"
          value={fuel}
          onChange={(e) => setFuel(e.target.value as FuelType)}
          className="flex h-10 w-full rounded-lg border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          {(Object.keys(FUEL_LABELS) as FuelType[]).map((f) => (
            <option key={f} value={f}>
              {FUEL_LABELS[f]}
            </option>
          ))}
        </select>
      </div>

      {/* Per-type fields */}
      {meta.fields.includes("threshold_price") && (
        <div className="space-y-1.5">
          <Label htmlFor="alert-price">Precio objetivo (€/L)</Label>
          <Input
            id="alert-price"
            type="number"
            inputMode="decimal"
            step="0.01"
            min="0"
            placeholder="1.42"
            value={thresholdPrice}
            onChange={(e) => setThresholdPrice(e.target.value)}
          />
        </div>
      )}

      {meta.fields.includes("threshold_pct") && (
        <div className="space-y-1.5">
          <Label htmlFor="alert-pct">Variación mínima (%)</Label>
          <Input
            id="alert-pct"
            type="number"
            inputMode="decimal"
            step="0.1"
            min="0"
            placeholder="2"
            value={thresholdPct}
            onChange={(e) => setThresholdPct(e.target.value)}
          />
        </div>
      )}

      {meta.fields.includes("brand") && (
        <div className="space-y-1.5">
          <Label htmlFor="alert-brand">Marca</Label>
          <Input
            id="alert-brand"
            type="text"
            placeholder="Repsol, Cepsa, BP…"
            value={brand}
            onChange={(e) => setBrand(e.target.value)}
          />
        </div>
      )}

      {geoMissing && (
        <p className="rounded-lg bg-amber-100 px-3 py-2 text-xs text-amber-800 dark:bg-amber-900/30 dark:text-amber-300">
          Esta alerta necesita tu ubicación. Activa la geolocalización o busca una ciudad primero.
        </p>
      )}

      <Button type="button" onClick={handleSubmit} disabled={!canSubmit() || create.isPending} className="w-full">
        <Plus className="h-4 w-4" />
        {create.isPending ? "Creando…" : "Crear alerta"}
      </Button>
    </div>
  );
}
