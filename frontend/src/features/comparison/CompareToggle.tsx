import { Check, Scale } from "lucide-react";

import { cn } from "@/lib/utils";

import { MAX_COMPARE_STATIONS, useComparisonStore } from "./store";

interface CompareToggleProps {
  stationId: number;
}

/**
 * Per-card "add to comparison" control. Mirrors FavoriteButton's footprint so it
 * sits naturally beside it. Reads the store directly to avoid prop-drilling
 * through the list, and disables once the cap is reached.
 */
export function CompareToggle({ stationId }: CompareToggleProps) {
  const compareIds = useComparisonStore((s) => s.compareIds);
  const toggle = useComparisonStore((s) => s.toggle);

  const selected = compareIds.includes(stationId);
  const disabled = !selected && compareIds.length >= MAX_COMPARE_STATIONS;

  return (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation();
        toggle(stationId);
      }}
      disabled={disabled}
      aria-pressed={selected}
      aria-label={selected ? "Quitar de la comparación" : "Añadir a la comparación"}
      title={disabled ? `Máximo ${MAX_COMPARE_STATIONS} gasolineras` : undefined}
      className={cn(
        "rounded-full p-1 transition-colors",
        selected
          ? "bg-primary/10 text-primary"
          : "text-muted-foreground hover:bg-muted hover:text-foreground",
        disabled && "cursor-not-allowed opacity-40 hover:bg-transparent",
      )}
    >
      {selected ? <Check className="h-4 w-4" /> : <Scale className="h-4 w-4" />}
    </button>
  );
}
