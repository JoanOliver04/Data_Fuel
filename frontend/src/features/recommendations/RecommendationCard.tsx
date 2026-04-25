import { useState } from "react";

import { Car, ChevronDown, ChevronUp } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { FavoriteButton } from "@/features/favorites/FavoriteButton";
import { PriceHistoryChart } from "@/features/price-history/PriceHistoryChart";
import { usePriceHistory } from "@/features/price-history/hooks";
import { PredictionBadge } from "@/features/predictions/PredictionBadge";

import type { RecommendationItem } from "./types";
import { formatDrivingSummary } from "./utils";

interface RecommendationCardProps {
  item: RecommendationItem;
  rank: number;
}

export function RecommendationCard({ item, rank }: RecommendationCardProps) {
  const [showChart, setShowChart] = useState(false);
  const { data: history } = usePriceHistory(item.station_id, item.fuel_type, showChart);

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary text-sm font-bold text-primary-foreground">
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
              <p className="mt-0.5 text-xs text-muted-foreground">{item.address}</p>
            </div>
          </div>
          <div className="shrink-0 text-right">
            <p className="text-xl font-bold">{Number(item.total_cost).toFixed(2)} €</p>
            <p className="text-xs text-muted-foreground">total</p>
          </div>
        </div>

        <div className="mt-3 grid grid-cols-3 gap-2 border-t pt-3 text-sm">
          <div>
            <p className="text-xs text-muted-foreground">Precio</p>
            <p className="font-medium">{Number(item.price_per_liter).toFixed(3)} €/L</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Distancia</p>
            <p className="flex items-center gap-1 font-medium">
              <Car className="h-3 w-3 text-muted-foreground" aria-hidden />
              {formatDrivingSummary(item)}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Desglose</p>
            <p className="text-xs font-medium">
              {Number(item.fuel_cost).toFixed(2)} + {Number(item.travel_cost).toFixed(2)} €
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => setShowChart((prev) => !prev)}
          aria-expanded={showChart}
          aria-label="Mostrar historial de precios"
          className="mt-2 flex w-full items-center justify-center gap-1 text-xs text-muted-foreground transition-colors hover:text-foreground"
        >
          {showChart ? (
            <ChevronUp className="h-3 w-3" />
          ) : (
            <ChevronDown className="h-3 w-3" />
          )}
          {showChart ? "Ocultar historial" : "Ver historial"}
        </button>

        {showChart && (
          <div className="mt-2 border-t pt-2">
            <PriceHistoryChart data={history ?? []} />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
