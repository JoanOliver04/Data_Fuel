import { cn } from "@/lib/utils";
import { useSettingsStore } from "@/stores/settings.store";
import { useSearchStore } from "@/stores/search.store";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface FiltersModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  allBrands: string[];
}

export function FiltersModal({ open, onOpenChange, allBrands }: FiltersModalProps) {
  const { liters, kmCost, setLiters, setKmCost } = useSettingsStore();
  const { filterBrands, filterOpenNow, toggleBrand, setFilterBrands, setFilterOpenNow } =
    useSearchStore();

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Filtros avanzados</DialogTitle>
        </DialogHeader>

        <div className="space-y-5">
          {/* Open now */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold">Abierto ahora</p>
              <p className="text-xs text-muted-foreground">Solo gasolineras 24 h</p>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={filterOpenNow}
              onClick={() => setFilterOpenNow(!filterOpenNow)}
              className={cn(
                "relative h-6 w-11 shrink-0 rounded-full transition-colors duration-200",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                filterOpenNow ? "bg-primary" : "bg-muted",
              )}
            >
              <span
                className={cn(
                  "absolute top-0.5 h-5 w-5 rounded-full bg-white shadow-sm transition-transform duration-200",
                  filterOpenNow ? "translate-x-5" : "translate-x-0.5",
                )}
              />
            </button>
          </div>

          {/* Brands */}
          {allBrands.length > 0 && (
            <div className="space-y-2.5">
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold">Marcas</p>
                {filterBrands.length > 0 && (
                  <button
                    type="button"
                    onClick={() => setFilterBrands([])}
                    className="text-xs font-medium text-muted-foreground hover:text-foreground underline-offset-2 hover:underline"
                  >
                    Limpiar
                  </button>
                )}
              </div>
              <div className="flex flex-wrap gap-1.5">
                {allBrands.map((brand) => {
                  const selected = filterBrands.includes(brand);
                  return (
                    <button
                      key={brand}
                      type="button"
                      onClick={() => toggleBrand(brand)}
                      className={cn(
                        "rounded-full border px-3 py-1 text-xs font-semibold transition-all duration-150",
                        selected
                          ? "border-primary bg-primary/10 text-primary"
                          : "border-border bg-background text-muted-foreground hover:border-primary/40 hover:text-foreground",
                      )}
                    >
                      {brand}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Advanced options */}
          <div className="space-y-3 rounded-xl border bg-muted/30 p-4">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Opciones avanzadas
            </p>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label htmlFor="modal-liters" className="text-xs font-semibold">
                  Litros a repostar
                </label>
                <input
                  id="modal-liters"
                  type="number"
                  min={1}
                  max={200}
                  step={1}
                  value={liters}
                  onChange={(e) => setLiters(Number(e.target.value))}
                  className={cn(
                    "w-full rounded-lg border border-input bg-background px-3 py-2 text-sm font-medium",
                    "focus:outline-none focus:ring-2 focus:ring-ring/50",
                  )}
                />
              </div>
              <div className="space-y-1.5">
                <label htmlFor="modal-kmcost" className="text-xs font-semibold">
                  Coste/km (€)
                </label>
                <input
                  id="modal-kmcost"
                  type="number"
                  min={0}
                  max={5}
                  step={0.01}
                  value={kmCost}
                  onChange={(e) => setKmCost(Number(e.target.value))}
                  className={cn(
                    "w-full rounded-lg border border-input bg-background px-3 py-2 text-sm font-medium",
                    "focus:outline-none focus:ring-2 focus:ring-ring/50",
                  )}
                />
              </div>
            </div>
          </div>
        </div>

        <div className="flex justify-end pt-1">
          <button
            type="button"
            onClick={() => onOpenChange(false)}
            className="rounded-xl bg-primary px-6 py-2.5 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90"
          >
            Aplicar
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
