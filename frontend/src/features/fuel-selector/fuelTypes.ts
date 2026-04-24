import type { FuelType } from "@/types/fuel";

export interface FuelOption {
  value: FuelType;
  shortLabel: string;
  tooltip: string;
  icon: string;
  isPremium?: true;
}

export interface FuelGroup {
  label: string;
  icon: string;
  options: FuelOption[];
}

export const FUEL_GROUPS: FuelGroup[] = [
  {
    label: "Gasolina",
    icon: "⛽",
    options: [
      {
        value: "gasolina_95",
        shortLabel: "95",
        tooltip: "La gasolina más común",
        icon: "⛽",
      },
      {
        value: "gasolina_98",
        shortLabel: "98",
        tooltip: "Mayor rendimiento en motores específicos",
        icon: "⛽",
      },
    ],
  },
  {
    label: "Diésel",
    icon: "🚗",
    options: [
      {
        value: "gasoil",
        shortLabel: "Diésel",
        tooltip: "Mayor eficiencia en consumo",
        icon: "🚗",
      },
      {
        value: "gasoil_premium",
        shortLabel: "Premium",
        tooltip: "Versión mejorada del diésel",
        icon: "🚗",
        isPremium: true,
      },
    ],
  },
];

/** Flat list of all selectable options — useful for validation and tests. */
export const ALL_FUEL_OPTIONS: FuelOption[] = FUEL_GROUPS.flatMap((g) => g.options);
