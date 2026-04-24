import type { FuelType } from "@/types/fuel";
import { useSettingsStore } from "@/stores/settings.store";

export interface UseFuelPreferenceReturn {
  fuelType: FuelType;
  setFuelType: (value: FuelType) => void;
}

/**
 * Reads and persists the user's preferred fuel type via the settings store.
 * Backed by localStorage through Zustand's persist middleware.
 */
export function useFuelPreference(): UseFuelPreferenceReturn {
  const fuelType = useSettingsStore((s) => s.preferredFuel);
  const setFuelType = useSettingsStore((s) => s.setPreferredFuel);
  return { fuelType, setFuelType };
}
