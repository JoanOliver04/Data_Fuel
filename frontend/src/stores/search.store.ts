import { create } from "zustand";

export type SortBy = "price" | "distance" | "total";

interface SearchState {
  locationLabel: string;
  radius: number | undefined;
  sortBy: SortBy;
  filterBrands: string[];
  filterOpenNow: boolean;
  setLocationLabel: (label: string) => void;
  setRadius: (radius: number | undefined) => void;
  setSortBy: (sort: SortBy) => void;
  toggleBrand: (brand: string) => void;
  setFilterBrands: (brands: string[]) => void;
  setFilterOpenNow: (value: boolean) => void;
}

export const useSearchStore = create<SearchState>()((set) => ({
  locationLabel: "",
  radius: 20,
  sortBy: "price",
  filterBrands: [],
  filterOpenNow: false,
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
}));
