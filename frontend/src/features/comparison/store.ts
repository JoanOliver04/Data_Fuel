import { create } from "zustand";

/** Hard cap on simultaneous comparison — 2–3 keeps columns readable on mobile. */
export const MAX_COMPARE_STATIONS = 3;

interface ComparisonState {
  /** Selected station ids, in the order the user added them. */
  compareIds: number[];
  /** Whether the comparison dialog is open. */
  isOpen: boolean;
  /** Add/remove a station; silently no-ops when the cap is reached. */
  toggle: (id: number) => void;
  remove: (id: number) => void;
  clear: () => void;
  open: () => void;
  close: () => void;
}

export const useComparisonStore = create<ComparisonState>((set) => ({
  compareIds: [],
  isOpen: false,
  toggle: (id) =>
    set((s) => {
      if (s.compareIds.includes(id)) {
        return { compareIds: s.compareIds.filter((x) => x !== id) };
      }
      if (s.compareIds.length >= MAX_COMPARE_STATIONS) return s;
      return { compareIds: [...s.compareIds, id] };
    }),
  remove: (id) => set((s) => ({ compareIds: s.compareIds.filter((x) => x !== id) })),
  clear: () => set({ compareIds: [], isOpen: false }),
  open: () => set({ isOpen: true }),
  close: () => set({ isOpen: false }),
}));
