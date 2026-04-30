import { ArrowLeft, Calculator, Loader2, MapPin, TrendingDown } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { FuelSelector } from "@/features/fuel-selector/FuelSelector";
import { calcRealCost } from "@/features/simulator/simulatorUtils";
import { useSimulatorData } from "@/features/simulator/hooks";
import { useSettingsStore } from "@/stores/settings.store";
import { cn } from "@/lib/utils";
import type { FuelType } from "@/types/fuel";

// ── Constants ────────────────────────────────────────────────────────────────

const BAR_COLORS = [
  "#22c55e",
  "#4ade80",
  "#86efac",
  "#fde047",
  "#f59e0b",
  "#fb923c",
  "#f87171",
  "#ef4444",
  "#dc2626",
  "#b91c1c",
];

// ── useDebounce ───────────────────────────────────────────────────────────────

function useDebounce<T>(value: T, ms: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), ms);
    return () => clearTimeout(id);
  }, [value, ms]);
  return debounced;
}

// ── SliderField ───────────────────────────────────────────────────────────────

interface SliderFieldProps {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  display: string;
  onChange: (v: number) => void;
}

function SliderField({ label, value, min, max, step, display, onChange }: SliderFieldProps) {
  const pct = ((value - min) / (max - min)) * 100;
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-foreground">{label}</span>
        <span className="min-w-[72px] text-right text-sm font-semibold tabular-nums text-primary">
          {display}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className={cn(
          "h-2 w-full cursor-pointer appearance-none rounded-full",
          "[&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4",
          "[&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:cursor-pointer",
          "[&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-primary",
          "[&::-webkit-slider-thumb]:shadow-md",
          "[&::-moz-range-thumb]:h-4 [&::-moz-range-thumb]:w-4",
          "[&::-moz-range-thumb]:cursor-pointer [&::-moz-range-thumb]:rounded-full",
          "[&::-moz-range-thumb]:border-0 [&::-moz-range-thumb]:bg-primary",
        )}
        style={{
          background: `linear-gradient(to right, hsl(var(--primary)) ${pct}%, hsl(var(--muted)) ${pct}%)`,
        }}
      />
    </div>
  );
}

// ── FormulaDisplay ────────────────────────────────────────────────────────────

interface FormulaDisplayProps {
  liters: number;
  kmCost: number;
}

function FormulaDisplay({ liters, kmCost }: FormulaDisplayProps) {
  return (
    <div className="rounded-xl border border-border bg-muted/40 px-4 py-3">
      <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
        Fórmula activa
      </p>
      <p className="font-mono text-sm text-foreground">
        {"Cᵢ = ("}
        <span className="font-bold text-primary">{liters} L</span>
        {" · Pᵢ) + (Dᵢ · "}
        <span className="font-bold text-primary">{kmCost.toFixed(2)} €/km</span>
        {")"}
      </p>
    </div>
  );
}

// ── Simulator ─────────────────────────────────────────────────────────────────

export function Simulator() {
  const {
    userLat,
    userLon,
    preferredFuel,
    kmCost: storedKmCost,
    liters: storedLiters,
  } = useSettingsStore();

  const [liters, setLiters] = useState(
    Math.max(10, Math.min(80, storedLiters)),
  );
  const [kmCost, setKmCost] = useState(
    Math.max(0.05, Math.min(0.3, storedKmCost)),
  );
  const [radius, setRadius] = useState(20);
  const [fuelType, setFuelType] = useState<FuelType>(preferredFuel);

  const dLiters = useDebounce(liters, 300);
  const dKmCost = useDebounce(kmCost, 300);
  const dRadius = useDebounce(radius, 300);

  const hasLocation = userLat !== null && userLon !== null;

  const { data: stations, isLoading, isError } = useSimulatorData(
    hasLocation ? { lat: userLat!, lon: userLon!, fuelType } : null,
  );

  const rankedResults = useMemo(() => {
    if (!stations || stations.length === 0) return [];
    return stations
      .filter((s) => s.distance_km <= dRadius)
      .map((s) => ({
        ...s,
        simCost: calcRealCost(s.price_per_liter, s.distance_km, dLiters, dKmCost),
      }))
      .sort((a, b) => a.simCost - b.simCost)
      .slice(0, 10);
  }, [stations, dLiters, dKmCost, dRadius]);

  const chartData = rankedResults.map((s) => ({
    name: s.brand.length > 9 ? s.brand.slice(0, 9) + "…" : s.brand,
    cost: parseFloat(s.simCost.toFixed(2)),
    fullName: s.brand,
    locality: s.locality,
    price: s.price_per_liter,
    dist: s.distance_km,
  }));

  const best = rankedResults[0] ?? null;
  const worst = rankedResults[rankedResults.length - 1] ?? null;
  const savings = best && worst ? worst.simCost - best.simCost : 0;

  return (
    <div className="flex min-h-dvh flex-col bg-background">
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-40 border-b border-border bg-background/90 backdrop-blur-xl supports-[backdrop-filter]:bg-background/80">
        <div className="mx-auto flex max-w-screen-xl items-center gap-3 px-4 py-3">
          <Link to="/" aria-label="Volver">
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 rounded-lg text-muted-foreground hover:text-foreground"
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div className="flex items-center gap-2">
            <Calculator className="h-5 w-5 text-primary" />
            <h1 className="text-lg font-extrabold tracking-tight">
              Simulador de Costes
            </h1>
          </div>
        </div>
      </header>

      {/* ── No location state ───────────────────────────────────────────────── */}
      {!hasLocation ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-4 px-6 py-20 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-muted text-4xl">
            <MapPin className="h-8 w-8 text-muted-foreground" />
          </div>
          <div>
            <p className="font-semibold">Ubicación no configurada</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Activa la geolocalización en la pantalla principal para usar el simulador.
            </p>
          </div>
          <Link to="/">
            <Button size="sm" className="rounded-lg">
              Ir a inicio
            </Button>
          </Link>
        </div>
      ) : (
        /* ── Main content ──────────────────────────────────────────────────── */
        <div className="mx-auto grid w-full max-w-screen-xl flex-1 grid-cols-1 gap-0 lg:grid-cols-[360px_1fr]">

          {/* ── LEFT PANEL — controls ─────────────────────────────────────── */}
          <aside className="border-b border-border bg-background px-5 py-6 lg:border-b-0 lg:border-r lg:overflow-y-auto">
            <div className="space-y-6">

              {/* Sliders */}
              <section className="space-y-5">
                <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Parámetros
                </h2>
                <SliderField
                  label="Litros a repostar"
                  value={liters}
                  min={10}
                  max={80}
                  step={1}
                  display={`${liters} L`}
                  onChange={setLiters}
                />
                <SliderField
                  label="Coste por km (K)"
                  value={kmCost}
                  min={0.05}
                  max={0.3}
                  step={0.01}
                  display={`${kmCost.toFixed(2)} €/km`}
                  onChange={setKmCost}
                />
                <SliderField
                  label="Radio de búsqueda"
                  value={radius}
                  min={5}
                  max={40}
                  step={5}
                  display={`${radius} km`}
                  onChange={setRadius}
                />
              </section>

              {/* Fuel selector */}
              <section className="space-y-3">
                <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Combustible
                </h2>
                <FuelSelector value={fuelType} onChange={setFuelType} compact />
              </section>

              {/* Live formula */}
              <FormulaDisplay liters={liters} kmCost={kmCost} />
            </div>
          </aside>

          {/* ── RIGHT PANEL — results ─────────────────────────────────────── */}
          <section className="flex flex-col gap-5 overflow-y-auto px-5 py-6">

            {/* Loading */}
            {isLoading && (
              <div className="flex flex-1 flex-col items-center justify-center gap-3 py-20">
                <Loader2 className="h-7 w-7 animate-spin text-primary" />
                <p className="text-sm text-muted-foreground">Cargando estaciones…</p>
              </div>
            )}

            {/* Error */}
            {isError && !isLoading && (
              <Card className="border-destructive/30 bg-destructive/5">
                <CardContent className="py-6 text-center text-sm text-destructive">
                  No se pudieron cargar las estaciones. Inténtalo de nuevo.
                </CardContent>
              </Card>
            )}

            {/* Empty results */}
            {!isLoading && !isError && rankedResults.length === 0 && (
              <div className="flex flex-1 flex-col items-center justify-center gap-3 py-20 text-center">
                <div className="text-4xl">🔍</div>
                <p className="font-semibold">Sin resultados</p>
                <p className="text-sm text-muted-foreground">
                  Prueba a ampliar el radio de búsqueda o cambiar el combustible.
                </p>
              </div>
            )}

            {!isLoading && !isError && rankedResults.length > 0 && (
              <>
                {/* ── Bar chart ─────────────────────────────────────────── */}
                <Card>
                  <CardContent className="px-3 pb-4 pt-4">
                    <h3 className="mb-3 text-sm font-semibold">
                      Top {rankedResults.length} — Coste Real (€)
                    </h3>
                    <ResponsiveContainer width="100%" height={260}>
                      <BarChart
                        data={chartData}
                        margin={{ top: 4, right: 8, left: 0, bottom: 64 }}
                      >
                        <XAxis
                          dataKey="name"
                          tick={{ fontSize: 11 }}
                          tickLine={false}
                          axisLine={false}
                          angle={-35}
                          textAnchor="end"
                          interval={0}
                        />
                        <YAxis
                          tick={{ fontSize: 11 }}
                          tickLine={false}
                          axisLine={false}
                          tickFormatter={(v: number) => `${v.toFixed(0)}€`}
                          width={48}
                        />
                        <RechartsTooltip
                          cursor={{ fill: "hsl(var(--muted))", opacity: 0.6 }}
                          content={({ active, payload }) => {
                            if (!active || !payload?.length) return null;
                            const d = payload[0]?.payload as (typeof chartData)[number];
                            return (
                              <div className="rounded-lg border border-border bg-background px-3 py-2 shadow-lg text-xs">
                                <p className="font-semibold">{d.fullName}</p>
                                <p className="text-muted-foreground">{d.locality}</p>
                                <div className="mt-1 space-y-0.5 border-t border-border pt-1">
                                  <p>
                                    Precio:{" "}
                                    <span className="font-medium">
                                      {d.price.toFixed(3)} €/L
                                    </span>
                                  </p>
                                  <p>
                                    Distancia:{" "}
                                    <span className="font-medium">
                                      {d.dist.toFixed(1)} km
                                    </span>
                                  </p>
                                  <p>
                                    Coste Real:{" "}
                                    <span className="font-semibold text-primary">
                                      {d.cost.toFixed(2)} €
                                    </span>
                                  </p>
                                </div>
                              </div>
                            );
                          }}
                        />
                        <Bar
                          dataKey="cost"
                          radius={[4, 4, 0, 0]}
                          isAnimationActive
                          animationDuration={400}
                          animationEasing="ease-out"
                        >
                          {chartData.map((_, i) => (
                            <Cell
                              key={i}
                              fill={BAR_COLORS[i] ?? BAR_COLORS[BAR_COLORS.length - 1]}
                            />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>

                {/* ── Summary card ──────────────────────────────────────── */}
                {best && (
                  <Card className="border-green-200 bg-green-50 dark:border-green-900/50 dark:bg-green-950/20">
                    <CardContent className="flex items-start gap-3 px-4 py-3">
                      <TrendingDown className="mt-0.5 h-5 w-5 shrink-0 text-green-600 dark:text-green-400" />
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-green-800 dark:text-green-300">
                          Mejor opción:{" "}
                          <span className="text-green-700 dark:text-green-400">
                            {best.brand}
                          </span>{" "}
                          · {best.locality}
                        </p>
                        <p className="mt-0.5 text-xs text-green-700 dark:text-green-500">
                          Coste Real:{" "}
                          <span className="font-bold">
                            {best.simCost.toFixed(2)} €
                          </span>
                          {savings > 0.005 && (
                            <>
                              {" · "}
                              <span className="font-medium">
                                Ahorras {savings.toFixed(2)} € vs la más cara
                              </span>
                            </>
                          )}
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* ── Data table ────────────────────────────────────────── */}
                <Card>
                  <CardContent className="p-0">
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-border bg-muted/40">
                            <th className="py-2.5 pl-4 pr-2 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                              #
                            </th>
                            <th className="px-2 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                              Estación
                            </th>
                            <th className="px-2 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                              Marca
                            </th>
                            <th className="px-2 py-2.5 text-right text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                              €/L
                            </th>
                            <th className="px-2 py-2.5 text-right text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                              Dist.
                            </th>
                            <th className="py-2.5 pl-2 pr-4 text-right text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                              Coste Real
                            </th>
                          </tr>
                        </thead>
                        <tbody>
                          {rankedResults.map((s, i) => {
                            const isBest = i === 0;
                            return (
                              <tr
                                key={s.station_id}
                                className={cn(
                                  "border-b border-border/50 last:border-b-0 transition-colors",
                                  isBest
                                    ? "bg-green-50/60 dark:bg-green-950/20"
                                    : "hover:bg-muted/30",
                                )}
                              >
                                <td className="py-2.5 pl-4 pr-2">
                                  <span
                                    className={cn(
                                      "inline-flex h-5 w-5 items-center justify-center rounded-full text-[11px] font-bold",
                                      isBest
                                        ? "bg-green-500 text-white"
                                        : "bg-muted text-muted-foreground",
                                    )}
                                  >
                                    {i + 1}
                                  </span>
                                </td>
                                <td className="max-w-[140px] truncate px-2 py-2.5 text-xs">
                                  <span className="font-medium">{s.locality}</span>
                                  <span className="ml-1 text-muted-foreground">
                                    {s.municipality !== s.locality && s.municipality}
                                  </span>
                                </td>
                                <td className="px-2 py-2.5 text-xs text-muted-foreground">
                                  {s.brand}
                                </td>
                                <td className="px-2 py-2.5 text-right text-xs tabular-nums">
                                  {s.price_per_liter.toFixed(3)}
                                </td>
                                <td className="px-2 py-2.5 text-right text-xs tabular-nums text-muted-foreground">
                                  {s.distance_km.toFixed(1)} km
                                </td>
                                <td
                                  className={cn(
                                    "py-2.5 pl-2 pr-4 text-right text-xs font-semibold tabular-nums",
                                    isBest ? "text-green-700 dark:text-green-400" : "",
                                  )}
                                >
                                  {s.simCost.toFixed(2)} €
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </CardContent>
                </Card>
              </>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
