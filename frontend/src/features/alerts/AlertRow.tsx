import { Trash2 } from "lucide-react";

import { cn } from "@/lib/utils";
import { getFuelLabel } from "@/types/fuel";
import type { FuelType } from "@/types/fuel";

import { useDeleteAlert, useUpdateAlert } from "./hooks";
import { alertMeta, TONE_CLASSES } from "./registry";
import type { Alert } from "./types";

// ── Smart Fuel Alerts — active alert row ──────────────────────────────────────
// Manage one configured alert: a human summary of what it watches, an instant
// enable/disable switch (optimistic) and delete. Mobile-first: the whole row is
// comfortable to tap, controls stay ≥ 40px.

function describe(alert: Alert): string {
  const fuel = getFuelLabel(alert.fuel_type as FuelType);
  switch (alert.alert_type) {
    case "PRICE_BELOW_THRESHOLD":
      return alert.threshold_price !== null
        ? `${fuel} por debajo de ${Number(alert.threshold_price).toFixed(2)} €/L`
        : fuel;
    case "CHEAPEST_BRAND":
      return `${alert.brand ?? "Marca"} más barata · ${fuel} · ${alert.radius_km.toFixed(0)} km`;
    case "TOTAL_COST_DROP":
      return `Coste total de ${fuel} baja ≥ ${alert.threshold_pct?.toFixed(1) ?? "?"}%`;
    case "PRICE_CHANGE":
      return `${fuel} cambia ≥ ${alert.threshold_pct?.toFixed(1) ?? "?"}% en 7 días`;
    case "WAIT_VS_REFUEL_SIGNAL":
      return `Esperar si se prevé ahorro ≥ ${alert.threshold_pct?.toFixed(1) ?? "?"}% · ${fuel}`;
    case "PREDICTION_TREND":
      return `Tendencia prevista de ${fuel} ≥ ${alert.threshold_pct?.toFixed(1) ?? "0.5"}%`;
    case "FAVORITE_STATION_CHANGE":
      return `Cambios de precio · ${fuel}`;
    case "WEEKLY_SUMMARY":
      return `Resumen semanal · ${fuel}`;
    default:
      return fuel;
  }
}

export function AlertRow({ alert, userId }: { alert: Alert; userId: string }) {
  const update = useUpdateAlert(userId);
  const remove = useDeleteAlert(userId);
  const meta = alertMeta(alert.alert_type);
  const tone = TONE_CLASSES[meta.tone];
  const Icon = meta.icon;

  return (
    <div
      className={cn(
        "flex items-center gap-3 rounded-xl border border-border bg-card px-3 py-2.5",
        !alert.is_enabled && "opacity-60",
      )}
    >
      <span className={cn("flex h-9 w-9 shrink-0 items-center justify-center rounded-lg", tone.chip)}>
        <Icon className={cn("h-4 w-4", tone.icon)} aria-hidden />
      </span>

      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold text-foreground">{meta.short}</p>
        <p className="truncate text-xs text-muted-foreground">{describe(alert)}</p>
      </div>

      {/* Enable switch */}
      <button
        type="button"
        role="switch"
        aria-checked={alert.is_enabled}
        aria-label={alert.is_enabled ? "Desactivar alerta" : "Activar alerta"}
        onClick={() => update.mutate({ id: alert.id, body: { is_enabled: !alert.is_enabled } })}
        className={cn(
          "relative h-6 w-11 shrink-0 rounded-full transition-colors",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1",
          alert.is_enabled ? "bg-primary" : "bg-muted-foreground/30",
        )}
      >
        <span
          className={cn(
            "absolute top-0.5 h-5 w-5 rounded-full bg-white shadow-sm transition-transform",
            alert.is_enabled ? "translate-x-[22px]" : "translate-x-0.5",
          )}
        />
      </button>

      <button
        type="button"
        onClick={() => remove.mutate(alert.id)}
        aria-label="Eliminar alerta"
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive"
      >
        <Trash2 className="h-4 w-4" />
      </button>
    </div>
  );
}
