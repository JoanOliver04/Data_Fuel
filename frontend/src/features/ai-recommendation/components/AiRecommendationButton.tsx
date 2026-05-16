import { Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useSettingsStore } from "@/stores/settings.store";

import { useAiRecommendation } from "../hooks";
import type { AiRecommendationRequest, AiRecommendationResponse } from "../types";

interface AiRecommendationButtonProps {
  municipio: string;
  comarca: string;
  precioActual: number;
  onResult: (result: AiRecommendationResponse) => void;
}

export function AiRecommendationButton({
  municipio,
  comarca,
  precioActual,
  onResult,
}: AiRecommendationButtonProps) {
  const { userLat, userLon, preferredFuel } = useSettingsStore();
  const { mutate, isPending, isError } = useAiRecommendation();

  const canFire = userLat !== null && userLon !== null && precioActual > 0;

  function handleClick() {
    if (!canFire) return;
    const payload: AiRecommendationRequest = {
      lat: userLat!,
      lon: userLon!,
      fuel_type: preferredFuel,
      municipio,
      comarca,
      precio_actual: precioActual,
    };
    mutate(payload, { onSuccess: onResult });
  }

  return (
    <div className="space-y-1">
      <Button
        onClick={handleClick}
        disabled={!canFire || isPending}
        className="w-full gap-2 bg-violet-600 text-white hover:bg-violet-700 dark:bg-violet-500 dark:hover:bg-violet-600"
      >
        <Sparkles className="h-4 w-4 shrink-0" />
        {isPending ? "Analizando precio…" : "Recomendación IA"}
      </Button>

      {isError && (
        <p className="text-center text-xs text-destructive">
          No se pudo obtener la recomendación. Inténtalo de nuevo.
        </p>
      )}
    </div>
  );
}
