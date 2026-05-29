import { create } from "zustand";

export type SnapPoint = "peek" | "half" | "full";

interface UiState {
  snap: SnapPoint;
  setSnap: (s: SnapPoint) => void;
}

export const useUiStore = create<UiState>((set) => ({
  snap: "half",
  setSnap: (snap) => set({ snap }),
}));
