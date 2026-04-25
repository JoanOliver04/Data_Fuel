import { useEffect, useState } from "react";

import { Car, Fuel, Route, Trees } from "lucide-react";

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

function computeKmCost(consumption: number, fuelPrice: number): number {
  if (consumption === 0) return 0;
  return (consumption / 100) * fuelPrice;
}

export function VehicleProfileForm({ initial, onSave, onCancel, isSaving }: VehicleProfileFormProps) {
  const [name, setName] = useState(initial?.name ?? "");
  const [consumption, setConsumption] = useState(initial?.fuel_consumption_per_100km ?? 7);
  const [tankCapacity, setTankCapacity] = useState(initial?.tank_capacity_litres ?? 50);
  const [drivingStyle, setDrivingStyle] = useState<DrivingStyle>(initial?.driving_style ?? "mixed");
  const [refFuelPrice, setRefFuelPrice] = useState(1.5);

  useEffect(() => {
    if (initial) {
      setName(initial.name);
      setConsumption(initial.fuel_consumption_per_100km);
      setTankCapacity(initial.tank_capacity_litres);
      setDrivingStyle(initial.driving_style);
    }
  }, [initial]);

  const estimatedKmCost = computeKmCost(consumption, refFuelPrice);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onSave({
      name,
      fuel_consumption_per_100km: consumption,
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

      {/* Consumption slider */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label htmlFor="vp-consumption">Consumo ({consumption.toFixed(1)} L/100km)</Label>
          <span className="flex items-center gap-1 text-xs text-muted-foreground">
            <Fuel className="h-3 w-3" />
            0 = eléctrico
          </span>
        </div>
        <input
          id="vp-consumption"
          type="range"
          min={0}
          max={15}
          step={0.1}
          value={consumption}
          onChange={(e) => setConsumption(Number(e.target.value))}
          className="h-2 w-full cursor-pointer appearance-none rounded-full bg-muted accent-primary"
        />
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>0 (eléctrico)</span>
          <span>15 L/100km</span>
        </div>
      </div>

      {/* Tank capacity */}
      <div className="space-y-1.5">
        <Label htmlFor="vp-tank">Depósito ({tankCapacity} L)</Label>
        <input
          id="vp-tank"
          type="range"
          min={10}
          max={120}
          step={1}
          value={tankCapacity}
          onChange={(e) => setTankCapacity(Number(e.target.value))}
          className="h-2 w-full cursor-pointer appearance-none rounded-full bg-muted accent-primary"
        />
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>10 L</span>
          <span>120 L</span>
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

      {/* Live preview */}
      <Card className="border-primary/30 bg-primary/5">
        <CardContent className="p-4">
          <p className="text-xs font-medium text-muted-foreground">Coste estimado por km</p>
          <p className="mt-1 text-2xl font-bold text-primary">
            {consumption === 0 ? "0.000" : estimatedKmCost.toFixed(3)} €/km
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            {consumption === 0
              ? "Vehículo eléctrico — sin coste de combustible"
              : `${consumption.toFixed(1)} L/100km × ${refFuelPrice.toFixed(2)} €/L ÷ 100`}
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
