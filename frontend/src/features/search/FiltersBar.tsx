import { Settings2 } from "lucide-react";
import { useState } from "react";

import { cn } from "@/lib/utils";
import { FuelSelector } from "@/features/fuel-selector/FuelSelector";
import { useSettingsStore } from "@/stores/settings.store";
import { useSearchStore } from "@/stores/search.store";
import type { SortBy } from "@/stores/search.store";

import { FiltersModal } from "./FiltersModal";

const RADIUS_OPTIONS: { label: string; value: number | undefined }[] = [
  { label: "10 km", value: 10 },
  { label: "20 km", value: 20 },
  { label: "40 km", value: 40 },
  { label: "Todos", value: undefined },
];

const SORT_OPTIONS: { label: string; value: SortBy }[] = [
  { label: "Precio", value: "price" },
  { label: "Distancia", value: "distance" },
  { label: "Coste Real", value: "total" },
];

interface FiltersBarProps {
  allBrands: string[];
}

export function FiltersBar({ allBrands }: FiltersBarProps) {
  const { preferredFuel, setPreferredFuel } = useSettingsStore();
  const { radius, sortBy, filterBrands, filterOpenNow, setRadius, setSortBy } = useSearchStore();
  const [modalOpen, setModalOpen] = useState(false);

  const activeFilterCount = filterBrands.length + (filterOpenNow ? 1 : 0);

  return (
    <>
      <div
        role="toolbar"
        aria-label="Filtros de búsqueda"
        className="flex items-center gap-2 overflow-x-auto pb-0.5 [&::-webkit-scrollbar]:hidden"
        style={{ scrollbarWidth: "none" }}
      >
        {/* Fuel selector (compact) */}
        <div className="flex flex-shrink-0 items-center rounded-xl bg-muted/60 px-1.5 py-1">
          <FuelSelector value={preferredFuel} onChange={setPreferredFuel} compact />
        </div>

        <div className="h-5 w-px flex-shrink-0 bg-border" />

        {/* Radius pills */}
        <div className="flex flex-shrink-0 gap-1">
          {RADIUS_OPTIONS.map((opt) => (
            <button
              key={String(opt.value)}
              type="button"
              onClick={() => setRadius(opt.value)}
              className={cn(
                "rounded-xl px-3 py-1.5 text-xs font-medium transition-all duration-150",
                radius === opt.value
                  ? "bg-primary text-primary-foreground shadow-sm scale-105"
                  : "bg-muted text-muted-foreground hover:bg-accent hover:text-accent-foreground",
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>

        <div className="h-5 w-px flex-shrink-0 bg-border" />

        {/* Sort pills */}
        <div className="flex flex-shrink-0 gap-1">
          {SORT_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => setSortBy(opt.value)}
              className={cn(
                "rounded-xl px-3 py-1.5 text-xs font-medium transition-all duration-150",
                sortBy === opt.value
                  ? "bg-primary text-primary-foreground shadow-sm scale-105"
                  : "bg-muted text-muted-foreground hover:bg-accent hover:text-accent-foreground",
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>

        <div className="h-5 w-px flex-shrink-0 bg-border" />

        {/* Filters button */}
        <button
          type="button"
          onClick={() => setModalOpen(true)}
          className={cn(
            "flex flex-shrink-0 items-center gap-1.5 rounded-xl px-3 py-1.5 text-xs font-medium transition-all duration-150",
            activeFilterCount > 0
              ? "bg-primary text-primary-foreground shadow-sm"
              : "bg-muted text-muted-foreground hover:bg-accent hover:text-accent-foreground",
          )}
        >
          <Settings2 className="h-3.5 w-3.5" />
          Filtros
          {activeFilterCount > 0 && (
            <span className="flex h-4 w-4 items-center justify-center rounded-full bg-white/20 text-[10px] font-bold">
              {activeFilterCount}
            </span>
          )}
        </button>
      </div>

      <FiltersModal open={modalOpen} onOpenChange={setModalOpen} allBrands={allBrands} />
    </>
  );
}
