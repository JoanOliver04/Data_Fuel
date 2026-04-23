/** Mirrors the backend FuelType enum (app/domain/entities/fuel_type.py). */
export type FuelType =
  | "gasoline_95_e5"
  | "gasoline_95_e10"
  | "gasoline_98_e5"
  | "diesel_a"
  | "diesel_premium";

export const FUEL_LABELS: Record<FuelType, string> = {
  gasoline_95_e5: "Gasolina 95 E5",
  gasoline_95_e10: "Gasolina 95 E10",
  gasoline_98_e5: "Gasolina 98 E5",
  diesel_a: "Gasóleo A",
  diesel_premium: "Gasóleo Premium",
};
