import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { FuelType } from "@/types/fuel";

const DEFAULT_KM_COST = 0.13;
const DEFAULT_LITERS = 40;

interface SettingsState {
  kmCost: number;
  liters: number;
  preferredFuel: FuelType;
  setKmCost: (value: number) => void;
  setLiters: (value: number) => void;
  setPreferredFuel: (value: FuelType) => void;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      kmCost: DEFAULT_KM_COST,
      liters: DEFAULT_LITERS,
      preferredFuel: "gasoline_95_e5",
      setKmCost: (value) => set({ kmCost: value }),
      setLiters: (value) => set({ liters: value }),
      setPreferredFuel: (value) => set({ preferredFuel: value }),
    }),
    { name: "datafuel-settings" },
  ),
);
