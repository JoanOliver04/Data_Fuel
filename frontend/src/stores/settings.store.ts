import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { FuelType } from "@/types/fuel";
import {
  DEFAULT_OPTIMIZATION_PROFILE,
  type OptimizationProfile,
} from "@/features/optimization/types";

const DEFAULT_KM_COST = 0.13;
const DEFAULT_LITERS = 40;

export type Theme = "light" | "dark";

/**
 * Stable per-device identifier for the (auth-less) alert API, which scopes every
 * alert/notification by `user_identifier`. Generated once and persisted, so a
 * user's alerts survive reloads and stay private to this device.
 */
function createUserId(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `u-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

interface SettingsState {
  kmCost: number;
  liters: number;
  preferredFuel: FuelType;
  userLat: number | null;
  userLon: number | null;
  favorites: number[];
  theme: Theme;
  activeVehicleProfileId: number | null;
  optimizationProfile: OptimizationProfile;
  alertsUserId: string;
  setKmCost: (value: number) => void;
  setLiters: (value: number) => void;
  setPreferredFuel: (value: FuelType) => void;
  setLocation: (lat: number, lon: number) => void;
  toggleFavorite: (stationId: number) => void;
  setTheme: (theme: Theme) => void;
  setActiveVehicleProfileId: (id: number | null) => void;
  setOptimizationProfile: (profile: OptimizationProfile) => void;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      kmCost: DEFAULT_KM_COST,
      liters: DEFAULT_LITERS,
      preferredFuel: "gasolina_95",
      userLat: null,
      userLon: null,
      favorites: [],
      theme: (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light") satisfies Theme,
      activeVehicleProfileId: null,
      optimizationProfile: DEFAULT_OPTIMIZATION_PROFILE,
      alertsUserId: createUserId(),
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
      setTheme: (theme) => set({ theme }),
      setActiveVehicleProfileId: (id) => set({ activeVehicleProfileId: id }),
      setOptimizationProfile: (profile) => set({ optimizationProfile: profile }),
    }),
    { name: "datafuel-settings" },
  ),
);
