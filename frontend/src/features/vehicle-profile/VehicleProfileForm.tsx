import { useEffect, useState } from "react";

import { Car, Route, Trees } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

import type { DrivingStyle, VehicleProfile, VehicleProfileCreate } from "./types";

interface VehicleProfileFormProps {
  initial?: VehicleProfile | undefined;
  onSave: (data: VehicleProfileCreate) => void;
  onCancel?: (() => void) | undefined;
  isSaving?: boolean | undefined;
}

const DRIVING_STYLE_OPTIONS: { value: DrivingStyle; label: string; icon: React.ReactNode }[] = [
  { value: "urban", label: "Urbano", icon: <Trees className="h-4 w-4" /> },
  { value: "mixed", label: "Mixto", icon: <Route className="h-4 w-4" /> },
  { value: "highway", label: "Carretera", icon: <Car className="h-4 w-4" /> },
];

const URBAN_MIN = 3;
const URBAN_MAX = 20;
const MIXED_MIN = 3;
const MIXED_MAX = 18;
const HIGHWAY_MIN = 3;
const HIGHWAY_MAX = 15;
const TANK_MIN = 10;
const TANK_MAX = 200;

function computeKmCost(consumption: number, fuelPrice: number): number {
  if (consumption === 0) return 0;
  return (consumption / 100) * fuelPrice;
}

export function VehicleProfileForm({ initial, onSave, onCancel, isSaving }: VehicleProfileFormProps) {
  const [name, setName] = useState(initial?.name ?? "");
  const [urban, setUrban] = useState(initial?.fuel_consumption_urban ?? 8);
  const [mixed, setMixed] = useState(initial?.fuel_consumption_mixed ?? 6.5);
  const [highway, setHighway] = useState(initial?.fuel_consumption_highway ?? 5.5);
  const [tankCapacity, setTankCapacity] = useState(initial?.tank_capacity_litres ?? 50);
  const [drivingStyle, setDrivingStyle] = useState<DrivingStyle>(initial?.driving_style ?? "mixed");
  const [refFuelPrice, setRefFuelPrice] = useState(1.5);

  useEffect(() => {
    if (initial) {
      setName(initial.name);
      setUrban(initial.fuel_consumption_urban);
      setMixed(initial.fuel_consumption_mixed);
      setHighway(initial.fuel_consumption_highway);
      setTankCapacity(initial.tank_capacity_litres);
      setDrivingStyle(initial.driving_style);
    }
  }, [initial]);

  const urbanKmCost = computeKmCost(urban, refFuelPrice);
  const mixedKmCost = computeKmCost(mixed, refFuelPrice);
  const highwayKmCost = computeKmCost(highway, refFuelPrice);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onSave({
      name,
      fuel_consumption_urban: urban,
      fuel_consumption_mixed: mixed,
      fuel_consumption_highway: highway,
      tank_capacity_litres: tankCapacity,
      driving_style: drivingStyle,
      reference_fuel_price: refFuelPrice,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* Vehicle name */}
      <div className="space-y-1.5">
        <Label htmlFor="vp-name">Nombre del vehículo</Label>
        <Input
          id="vp-name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Ej: Mi Coche"
          required
          maxLength={120}
          className="rounded-lg"
        />
      </div>

      {/* Consumption sliders */}
      <div className="space-y-4 rounded-xl border bg-muted/30 p-4">
        <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Consumo (L/100km)
        </p>
        <ConsumptionSlider
          id="vp-cons-urban"
          label="Consumo urbano"
          helper="Para gasolineras a menos de 5 km"
          value={urban}
          min={URBAN_MIN}
          max={URBAN_MAX}
          onChange={setUrban}
        />
        <ConsumptionSlider
          id="vp-cons-mixed"
          label="Combinado (por defecto)"
          helper="Para gasolineras entre 5 y 20 km"
          value={mixed}
          min={MIXED_MIN}
          max={MIXED_MAX}
          onChange={setMixed}
        />
        <ConsumptionSlider
          id="vp-cons-highway"
          label="Consumo carretera"
          helper="Para gasolineras a más de 20 km"
          value={highway}
          min={HIGHWAY_MIN}
          max={HIGHWAY_MAX}
          onChange={setHighway}
        />
      </div>

      {/* Tank capacity */}
      <div className="space-y-1.5">
        <Label htmlFor="vp-tank">
          Depósito — <span className="font-semibold">{tankCapacity} L</span>
        </Label>
        <input
          id="vp-tank"
          type="range"
          min={TANK_MIN}
          max={TANK_MAX}
          step={1}
          value={tankCapacity}
          onChange={(e) => setTankCapacity(Number(e.target.value))}
          className="h-2 w-full cursor-pointer appearance-none rounded-full bg-muted accent-primary"
        />
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>{TANK_MIN} L</span>
          <span>{TANK_MAX} L</span>
        </div>
      </div>

      {/* Driving style */}
      <div className="space-y-2">
        <Label>Estilo de conducción</Label>
        <div className="grid grid-cols-3 gap-2">
          {DRIVING_STYLE_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => setDrivingStyle(opt.value)}
              className={cn(
                "flex flex-col items-center gap-1.5 rounded-xl border p-3 text-xs font-semibold transition-all duration-150",
                drivingStyle === opt.value
                  ? "border-primary bg-primary/10 text-primary shadow-sm"
                  : "border-border bg-background text-muted-foreground hover:border-primary/30 hover:bg-muted/50",
              )}
            >
              {opt.icon}
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Reference fuel price */}
      <div className="space-y-1.5">
        <Label htmlFor="vp-ref-price">Precio referencia (€/L)</Label>
        <Input
          id="vp-ref-price"
          type="number"
          min={0.5}
          max={5}
          step={0.01}
          value={refFuelPrice}
          onChange={(e) => setRefFuelPrice(Number(e.target.value))}
          className="rounded-lg"
        />
        <p className="text-xs text-muted-foreground">
          Solo para la previsualización. No se guarda.
        </p>
      </div>

      {/* Live cost preview — 3-column grid */}
      <Card className="border-primary/20 bg-gradient-to-br from-primary/5 via-primary/3 to-transparent">
        <CardContent className="p-4">
          <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Coste estimado por km
          </p>
          <div className="grid grid-cols-3 divide-x divide-primary/20">
            <div className="pr-3 text-center">
              <p className="text-[20px] font-extrabold tabular-nums text-primary">
                {urbanKmCost.toFixed(3)}
              </p>
              <p className="text-[11px] font-medium text-muted-foreground">Urbano €/km</p>
            </div>
            <div className="px-3 text-center">
              <p className="text-[20px] font-extrabold tabular-nums text-primary">
                {mixedKmCost.toFixed(3)}
              </p>
              <p className="text-[11px] font-medium text-muted-foreground">Mixto €/km</p>
            </div>
            <div className="pl-3 text-center">
              <p className="text-[20px] font-extrabold tabular-nums text-primary">
                {highwayKmCost.toFixed(3)}
              </p>
              <p className="text-[11px] font-medium text-muted-foreground">Carretera €/km</p>
            </div>
          </div>
          <p className="mt-3 text-center text-xs text-muted-foreground">
            Ref: {refFuelPrice.toFixed(2)} €/L
          </p>
        </CardContent>
      </Card>

      {/* Actions */}
      <div className="flex gap-2 pt-1">
        <Button type="submit" disabled={isSaving} className="flex-1 rounded-lg font-semibold">
          {isSaving ? "Guardando…" : "Guardar perfil"}
        </Button>
        {onCancel && (
          <Button
            type="button"
            variant="ghost"
            onClick={onCancel}
            disabled={isSaving}
            className="rounded-lg"
          >
            Cancelar
          </Button>
        )}
      </div>
    </form>
  );
}

// ── ConsumptionSlider ─────────────────────────────────────────────────────────

interface ConsumptionSliderProps {
  id: string;
  label: string;
  helper: string;
  value: number;
  min: number;
  max: number;
  onChange: (value: number) => void;
}

function ConsumptionSlider({ id, label, helper, value, min, max, onChange }: ConsumptionSliderProps) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-baseline justify-between">
        <Label htmlFor={id} className="text-xs font-medium">
          {label}
        </Label>
        <span className="text-xs font-semibold text-primary tabular-nums">
          {value.toFixed(1)} L/100km
        </span>
      </div>
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={0.1}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="h-2 w-full cursor-pointer appearance-none rounded-full bg-muted accent-primary"
      />
      <div className="flex justify-between text-[10px] text-muted-foreground/70">
        <span>{min} L</span>
        <span className="text-center text-[10px] text-muted-foreground">{helper}</span>
        <span>{max} L</span>
      </div>
    </div>
  );
}
