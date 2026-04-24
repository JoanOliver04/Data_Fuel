/** Mirrors the backend FuelType enum (app/domain/entities/fuel_type.py). */
export type FuelType =
  | "gasolina_95"
  | "gasolina_95_e10"
  | "gasolina_98"
  | "gasoil"
  | "gasoil_premium";

export const FUEL_LABELS: Record<FuelType, string> = {
  gasolina_95: "Gasolina 95",
  gasolina_95_e10: "Gasolina 95 E10",
  gasolina_98: "Gasolina 98",
  gasoil: "Diésel",
  gasoil_premium: "Diésel Premium",
};

export function getFuelLabel(fuelType: FuelType): string {
  return FUEL_LABELS[fuelType];
}
