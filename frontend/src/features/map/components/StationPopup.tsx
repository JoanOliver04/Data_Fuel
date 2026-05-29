import {
  Clock,
  ExternalLink,
  Fuel,
  MapPin,
  Navigation,
  Star,
  Timer,
  TrendingDown,
  Zap,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { FavoriteButton } from "@/features/favorites/FavoriteButton";
import type { RecommendationItem } from "@/features/recommendations/types";
import {
  formatTrafficDelay,
  isStationOpenNow,
} from "@/features/recommendations/utils";
import { FUEL_LABELS } from "@/types/fuel";

// ── Rank metadata ──────────────────────────────────────────────────────────

const RANK_COLORS = ["#22c55e", "#f97316", "#ef4444"] as const;
const RANK_BG = ["#f0fdf4", "#fff7ed", "#fef2f2"] as const;
const RANK_LABELS = ["Mejor opción", "2ª opción", "3ª opción"] as const;

// ── Google Maps deep-link ──────────────────────────────────────────────────

function mapsUrl(lat: number, lon: number): string {
  return `https://www.google.com/maps/dir/?api=1&destination=${lat},${lon}`;
}

// ── Sub-components ─────────────────────────────────────────────────────────

function RankBadge({ rank }: { rank: number }) {
  const color = RANK_COLORS[rank - 1] ?? "#3b82f6";
  const bg = RANK_BG[rank - 1] ?? "#eff6ff";
  const label = RANK_LABELS[rank - 1] ?? `#${rank}`;
  return (
    <span
      className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold leading-none"
      style={{ color, background: bg }}
    >
      {rank === 1 && <Star className="h-2.5 w-2.5 fill-current" />}
      {label}
    </span>
  );
}

function PriceChip({
  label,
  price,
  active,
}: {
  label: string;
  price: number;
  active: boolean;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center rounded-xl px-3 py-2 text-center transition-colors",
        active
          ? "bg-primary text-primary-foreground shadow-sm"
          : "bg-muted/60 text-foreground",
      )}
    >
      <span className="text-[10px] font-medium leading-none opacity-80">{label}</span>
      <span className="mt-1 text-sm font-bold leading-none tabular-nums">
        {price.toFixed(3)}
        <span className="text-[10px] font-normal opacity-80"> €/L</span>
      </span>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────

interface StationPopupProps {
  item: RecommendationItem;
  rank: number;
  /** Savings in € versus the most expensive option in the current result set. */
  savings?: number;
  /** Called when user taps "Ver detalles" to scroll list to this station. */
  onViewDetails?: () => void;
}

export function StationPopup({ item, rank, savings, onViewDetails }: StationPopupProps) {
  const trafficDelay = formatTrafficDelay(item);
  const isOpen = isStationOpenNow(item.schedule);
  const rankColor = RANK_COLORS[rank - 1] ?? "#3b82f6";

  const hasDriving =
    item.driving_distance_km != null || item.driving_duration_min != null;
  const distanceKm = item.driving_distance_km ?? item.distance_km;
  const hasEta = item.eta_minutes != null;

  return (
    <div className="df-station-popup w-[272px]">
      {/* ── Header ──────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-2 px-4 pb-3 pt-4">
        <div className="min-w-0 flex-1">
          <RankBadge rank={rank} />
          <h3 className="mt-1.5 truncate text-base font-bold leading-tight tracking-tight text-foreground">
            {item.brand}
          </h3>
          <div className="mt-0.5 flex items-center gap-1.5">
            <span
              className={cn(
                "inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 text-[10px] font-medium",
                isOpen
                  ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                  : "bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400",
              )}
            >
              <span
                className={cn(
                  "h-1.5 w-1.5 rounded-full",
                  isOpen ? "bg-green-500" : "bg-red-500",
                )}
              />
              {isOpen ? "Abierto" : "Cerrado"}
            </span>
          </div>
        </div>
        <div className="-mt-0.5 shrink-0">
          <FavoriteButton stationId={item.station_id} />
        </div>
      </div>

      {/* ── Fuel price chip ─────────────────────────────────────────── */}
      <div className="border-t border-border/60 px-4 py-3">
        <div className="flex items-center gap-2">
          <PriceChip
            label={FUEL_LABELS[item.fuel_type]}
            price={item.price_per_liter}
            active
          />
          <div className="flex-1 rounded-xl bg-muted/60 px-3 py-2">
            <p className="text-[10px] font-medium text-muted-foreground">Coste total</p>
            <p className="mt-0.5 text-sm font-bold tabular-nums text-foreground">
              {item.total_cost.toFixed(2)}
              <span className="text-[10px] font-normal text-muted-foreground"> €</span>
            </p>
            <p className="text-[10px] text-muted-foreground">
              {item.liters} L
            </p>
          </div>
        </div>
      </div>

      {/* ── Smart insights ──────────────────────────────────────────── */}
      {(rank === 1 || (savings != null && savings > 0.01)) && (
        <div
          className="mx-4 mb-3 flex items-center gap-2 rounded-xl px-3 py-2"
          style={{ background: `${rankColor}14` }}
        >
          {rank === 1 ? (
            <TrendingDown className="h-3.5 w-3.5 shrink-0" style={{ color: rankColor }} />
          ) : (
            <Zap className="h-3.5 w-3.5 shrink-0" style={{ color: rankColor }} />
          )}
          <p className="text-[11px] font-medium" style={{ color: rankColor }}>
            {rank === 1 && savings != null && savings > 0.01
              ? `Ahorra ${savings.toFixed(2)} € vs otras opciones`
              : rank === 1
                ? "Opción más económica del ranking"
                : `Ahorra ${(savings ?? 0).toFixed(2)} € vs la más cara`}
          </p>
        </div>
      )}

      {/* ── Location & distance ─────────────────────────────────────── */}
      <div className="border-t border-border/60 px-4 py-3 space-y-1.5">
        <div className="flex items-start gap-2">
          <MapPin className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
          <div className="min-w-0">
            <p className="text-xs font-medium leading-tight text-foreground">
              {item.address}
            </p>
            <p className="text-[11px] text-muted-foreground">
              {item.locality}, {item.province}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Fuel className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-foreground tabular-nums">
              {distanceKm.toFixed(1)} km
            </span>
            {item.driving_duration_min != null && (
              <>
                <span className="text-muted-foreground/50">·</span>
                <span className="text-xs text-muted-foreground tabular-nums">
                  {Math.round(item.driving_duration_min)} min
                </span>
              </>
            )}
          </div>
        </div>

        {/* ETA / traffic — only when data exists */}
        {hasEta && (
          <div className="flex items-center gap-2">
            <Timer className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
            <span className="text-xs text-foreground tabular-nums">
              {Math.round(item.eta_minutes!)} min ETA
            </span>
            {trafficDelay && (
              <span className="inline-flex items-center gap-0.5 rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                <Clock className="h-2.5 w-2.5" />
                {trafficDelay} tráfico
              </span>
            )}
          </div>
        )}
      </div>

      {/* ── Actions ──────────────────────────────────────────────────── */}
      <div className="border-t border-border/60 px-4 pb-4 pt-3 space-y-2">
        {/* Primary CTA */}
        <a
          href={mapsUrl(item.latitude, item.longitude)}
          target="_blank"
          rel="noopener noreferrer"
          className={cn(
            "flex w-full items-center justify-center gap-2 rounded-xl px-4 py-3",
            "bg-primary text-primary-foreground text-sm font-semibold",
            "shadow-sm transition-all active:scale-[0.98] hover:brightness-110",
            "min-h-[48px]",
          )}
          aria-label={`Cómo llegar a ${item.brand}`}
        >
          <Navigation className="h-4 w-4" />
          Cómo llegar
        </a>

        {/* Secondary CTA */}
        {onViewDetails && (
          <button
            type="button"
            onClick={onViewDetails}
            className={cn(
              "flex w-full items-center justify-center gap-1.5 rounded-xl px-4 py-2.5",
              "bg-muted/70 text-foreground text-sm font-medium",
              "transition-all active:scale-[0.98] hover:bg-muted",
              "min-h-[44px]",
            )}
          >
            <ExternalLink className="h-3.5 w-3.5 text-muted-foreground" />
            Ver en lista
          </button>
        )}
      </div>
    </div>
  );
}
