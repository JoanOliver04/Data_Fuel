import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { FuelType } from "@/types/fuel";

const DEFAULT_KM_COST = 0.13;
const DEFAULT_LITERS = 40;

interface SettingsState {
  kmCost: number;
  liters: number;
  preferredFuel: FuelType;
  userLat: number | null;
  userLon: number | null;
  favorites: number[];
  setKmCost: (value: number) => void;
  setLiters: (value: number) => void;
  setPreferredFuel: (value: FuelType) => void;
  setLocation: (lat: number, lon: number) => void;
  toggleFavorite: (stationId: number) => void;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      kmCost: DEFAULT_KM_COST,
      liters: DEFAULT_LITERS,
      preferredFuel: "gasoline_95_e5",
      userLat: null,
      userLon: null,
      favorites: [],
      setKmCost: (value) => set({ kmCost: value }),
      setLiters: (value) => set({ liters: value }),
      setPreferredFuel: (value) => set({ preferredFuel: value }),
      setLocation: (lat, lon) => set({ userLat: lat, userLon: lon }),
      toggleFavorite: (stationId) =>
        set((state) => ({
          favorites: state.favorites.includes(stationId)
            ? state.favorites.filter((id) => id !== stationId)
            : [...state.favorites, stationId],
        })),
    }),
    { name: "datafuel-settings" },
  ),
);
