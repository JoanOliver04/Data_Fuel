import { useEffect, useState } from "react";

import { Car, Route, Trees } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

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

// Backend validation: 1.0–25.0 L/100km, tank 10–200 L. Sliders use the
// task-specified narrower ranges so the UI guides the user toward sensible
// values; backend enforces the hard limits.
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
      {/* Name */}
      <div className="space-y-1.5">
        <Label htmlFor="vp-name">Nombre del vehículo</Label>
        <Input
          id="vp-name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Ej: Mi Coche"
          required
          maxLength={120}
        />
      </div>

      {/* Urban consumption */}
      <ConsumptionSlider
        id="vp-cons-urban"
        label="Consumo urbano"
        helper="Aplicado para gasolineras a menos de 5 km"
        value={urban}
        min={URBAN_MIN}
        max={URBAN_MAX}
        onChange={setUrban}
      />

      {/* Mixed consumption */}
      <ConsumptionSlider
        id="vp-cons-mixed"
        label="Combinado (por defecto)"
        helper="Aplicado para gasolineras entre 5 y 20 km"
        value={mixed}
        min={MIXED_MIN}
        max={MIXED_MAX}
        onChange={setMixed}
      />

      {/* Highway consumption */}
      <ConsumptionSlider
        id="vp-cons-highway"
        label="Consumo carretera"
        helper="Aplicado para gasolineras a más de 20 km"
        value={highway}
        min={HIGHWAY_MIN}
        max={HIGHWAY_MAX}
        onChange={setHighway}
      />

      {/* Tank capacity */}
      <div className="space-y-1.5">
        <Label htmlFor="vp-tank">Depósito ({tankCapacity} L)</Label>
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
              className={`flex flex-col items-center gap-1 rounded-lg border p-3 text-xs font-medium transition-colors ${
                drivingStyle === opt.value
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-border bg-background hover:bg-muted"
              }`}
            >
              {opt.icon}
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Reference fuel price for preview */}
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
        />
        <p className="text-xs text-muted-foreground">
          Usado para calcular el coste por km. No se guarda.
        </p>
      </div>

      {/* Live preview — three estimated costs */}
      <Card className="border-primary/30 bg-primary/5">
        <CardContent className="p-4">
          <p className="text-xs font-medium text-muted-foreground">Coste estimado por km</p>
          <p className="mt-1 text-sm font-semibold text-primary">
            Urban km cost: {urbanKmCost.toFixed(2)} €/km · Mixed: {mixedKmCost.toFixed(2)} €/km ·
            Highway: {highwayKmCost.toFixed(2)} €/km
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            Calculado con {refFuelPrice.toFixed(2)} €/L de referencia.
          </p>
        </CardContent>
      </Card>

      <div className="flex gap-2 pt-1">
        <Button type="submit" disabled={isSaving} className="flex-1">
          {isSaving ? "Guardando…" : "Guardar perfil"}
        </Button>
        {onCancel && (
          <Button type="button" variant="ghost" onClick={onCancel} disabled={isSaving}>
            Cancelar
          </Button>
        )}
      </div>
    </form>
  );
}

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
      <Label htmlFor={id}>
        {label} ({value.toFixed(1)} L/100km)
      </Label>
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
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>{min} L/100km</span>
        <span>{max} L/100km</span>
      </div>
      <p className="text-xs text-muted-foreground">{helper}</p>
    </div>
  );
}
