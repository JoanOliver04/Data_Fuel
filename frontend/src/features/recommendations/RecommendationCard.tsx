import { Card, CardContent } from "@/components/ui/card";
import { PredictionBadge } from "@/features/predictions/PredictionBadge";

import type { RecommendationItem } from "./types";

interface RecommendationCardProps {
  item: RecommendationItem;
  rank: number;
}

export function RecommendationCard({ item, rank }: RecommendationCardProps) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary text-sm font-bold text-primary-foreground">
              {rank}
            </span>
            <div>
              <div className="flex items-center gap-2">
                <p className="font-semibold">{item.brand}</p>
                <PredictionBadge stationId={item.station_id} fuelType={item.fuel_type} />
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
            <p className="font-medium">{item.distance_km.toFixed(1)} km</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Desglose</p>
            <p className="text-xs font-medium">
              {Number(item.fuel_cost).toFixed(2)} + {Number(item.travel_cost).toFixed(2)} €
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
