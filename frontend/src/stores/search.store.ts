import { create } from "zustand";

export type SortBy = "price" | "distance" | "total";

/** A coordinate the user dropped manually by pinning the map. */
export interface PinLocation {
  lat: number;
  lon: number;
}

interface SearchState {
  locationLabel: string;
  radius: number | undefined;
  sortBy: SortBy;
  filterBrands: string[];
  filterOpenNow: boolean;
  /** Station currently selected (via list click or marker click) */
  selectedStationId: number | null;
  /** Station currently hovered in the list */
  hoveredStationId: number | null;
  /** Whether map clicks currently drop/move the user pin. */
  pinModeActive: boolean;
  /** The manually-selected coordinate, or null when none has been placed. */
  pinLocation: PinLocation | null;
  setLocationLabel: (label: string) => void;
  setRadius: (radius: number | undefined) => void;
  setSortBy: (sort: SortBy) => void;
  toggleBrand: (brand: string) => void;
  setFilterBrands: (brands: string[]) => void;
  setFilterOpenNow: (value: boolean) => void;
  setSelectedStationId: (id: number | null) => void;
  setHoveredStationId: (id: number | null) => void;
  setPinModeActive: (active: boolean) => void;
  setPinLocation: (location: PinLocation | null) => void;
  /** Drop the manual pin and leave pin mode — used when another search source
   *  (GPS, municipality) explicitly takes over the location. */
  clearPin: () => void;
}

export const useSearchStore = create<SearchState>()((set) => ({
  locationLabel: "",
  radius: 20,
  sortBy: "price",
  filterBrands: [],
  filterOpenNow: false,
  selectedStationId: null,
  hoveredStationId: null,
  pinModeActive: false,
  pinLocation: null,
  setLocationLabel: (locationLabel) => set({ locationLabel }),
  setRadius: (radius) => set({ radius }),
  setSortBy: (sortBy) => set({ sortBy }),
  toggleBrand: (brand) =>
    set((state) => ({
      filterBrands: state.filterBrands.includes(brand)
        ? state.filterBrands.filter((b) => b !== brand)
        : [...state.filterBrands, brand],
    })),
  setFilterBrands: (filterBrands) => set({ filterBrands }),
  setFilterOpenNow: (filterOpenNow) => set({ filterOpenNow }),
  setSelectedStationId: (selectedStationId) => set({ selectedStationId }),
  setHoveredStationId: (hoveredStationId) => set({ hoveredStationId }),
  setPinModeActive: (pinModeActive) => set({ pinModeActive }),
  setPinLocation: (pinLocation) => set({ pinLocation }),
  clearPin: () => set({ pinModeActive: false, pinLocation: null }),
}));
