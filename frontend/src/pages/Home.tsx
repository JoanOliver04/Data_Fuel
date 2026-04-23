import { Button } from "@/components/ui/button";
import { HealthBadge } from "@/features/health/HealthBadge";
import { FUEL_LABELS } from "@/types/fuel";
import { useSettingsStore } from "@/stores/settings.store";

export function Home() {
  const { liters, kmCost, preferredFuel, setLiters } = useSettingsStore();

  return (
    <main className="container py-10 space-y-6">
      <header className="space-y-2">
        <h1 className="text-3xl font-bold tracking-tight">Data Fuel ⛽</h1>
        <p className="text-muted-foreground">
          Encuentra la gasolinera más rentable según precio y distancia.
        </p>
        <HealthBadge />
      </header>

      <section className="rounded-lg border bg-card p-6 space-y-3">
        <h2 className="text-lg font-semibold">Configuración actual</h2>
        <ul className="text-sm space-y-1">
          <li>Litros a repostar: <strong>{liters}</strong></li>
          <li>Coste por km: <strong>{kmCost.toFixed(2)} €/km</strong></li>
          <li>Combustible preferido: <strong>{FUEL_LABELS[preferredFuel]}</strong></li>
        </ul>
        <Button onClick={() => setLiters(liters + 5)}>Sumar 5 L (demo)</Button>
      </section>
    </main>
  );
}
