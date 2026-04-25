import { useState } from "react";

import { Car, ChevronDown, ChevronUp, Info } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { FavoriteButton } from "@/features/favorites/FavoriteButton";
import { PriceHistoryChart } from "@/features/price-history/PriceHistoryChart";
import { usePriceHistory } from "@/features/price-history/hooks";
import { PredictionBadge } from "@/features/predictions/PredictionBadge";
import { useSettingsStore } from "@/stores/settings.store";
import { cn } from "@/lib/utils";

import type { RecommendationItem } from "./types";
import { formatDrivingSummary, formatRealCostTooltip } from "./utils";

function rankBadgeClass(rank: number): string {
  if (rank === 1)
    return "bg-gradient-to-br from-amber-300 via-amber-400 to-amber-600 ring-2 ring-amber-300/40 shadow-md shadow-amber-400/30";
  if (rank === 2) return "bg-gradient-to-br from-slate-200 via-slate-300 to-slate-500";
  if (rank === 3) return "bg-gradient-to-br from-orange-300 via-orange-400 to-orange-700";
  return "bg-primary";
}

interface RecommendationCardProps {
  item: RecommendationItem;
  rank: number;
}

export function RecommendationCard({ item, rank }: RecommendationCardProps) {
  const [showChart, setShowChart] = useState(false);
  const { data: history } = usePriceHistory(item.station_id, item.fuel_type, showChart);
  const activeVehicleProfileId = useSettingsStore((s) => s.activeVehicleProfileId);

  return (
    <Card>
      <CardContent className="p-4">
        {/* Header row */}
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <span
              className={cn(
                "flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[11px] font-bold text-white",
                rankBadgeClass(rank),
              )}
            >
              {rank}
            </span>
            <div>
              <div className="flex items-center gap-1.5">
                <p className="font-semibold">{item.brand}</p>
                <PredictionBadge stationId={item.station_id} fuelType={item.fuel_type} />
                <FavoriteButton stationId={item.station_id} />
              </div>
              <p className="text-sm text-muted-foreground">
                {item.locality}, {item.province}
              </p>
              <p className="mt-0.5 text-xs text-muted-foreground/70">{item.address}</p>
            </div>
          </div>

          {/* Total cost */}
          <div className="shrink-0 text-right">
            <p className="text-xl font-bold tabular-nums tracking-tight">
              {Number(item.total_cost).toFixed(2)} €
            </p>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <p className="mt-0.5 flex cursor-default items-center justify-end gap-0.5 text-xs text-muted-foreground">
                    total
                    <Info className="h-3 w-3" aria-hidden />
                  </p>
                </TooltipTrigger>
                <TooltipContent side="left">
                  {formatRealCostTooltip(item, activeVehicleProfileId !== null)}
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        </div>

        {/* Stats grid */}
        <div className="mt-3 grid grid-cols-3 divide-x divide-border border-t pt-3 text-sm">
          <div className="pr-3">
            <p className="text-xs text-muted-foreground">Precio</p>
            <p className="mt-0.5 font-semibold tabular-nums">
              {Number(item.price_per_liter).toFixed(3)} €/L
            </p>
          </div>
          <div className="px-3">
            <p className="text-xs text-muted-foreground">Distancia</p>
            <p className="mt-0.5 flex items-center gap-1 font-semibold">
              <Car className="h-3 w-3 shrink-0 text-muted-foreground" aria-hidden />
              {formatDrivingSummary(item)}
            </p>
          </div>
          <div className="pl-3">
            <p className="text-xs text-muted-foreground">Desglose</p>
            <p className="mt-0.5 text-xs font-semibold tabular-nums">
              {Number(item.fuel_cost).toFixed(2)} + {Number(item.travel_cost).toFixed(2)} €
            </p>
          </div>
        </div>

        {/* Price history toggle */}
        <button
          type="button"
          onClick={() => setShowChart((prev) => !prev)}
          aria-expanded={showChart}
          aria-label="Mostrar historial de precios"
          className="mt-2.5 flex w-full items-center justify-center gap-1.5 rounded-lg py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
        >
          {showChart ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
          {showChart ? "Ocultar historial" : "Ver historial de precios"}
        </button>

        {showChart && (
          <div className="mt-2 rounded-lg border bg-muted/30 p-3">
            <PriceHistoryChart data={history ?? []} />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
