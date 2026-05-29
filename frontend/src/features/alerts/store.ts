import { create } from "zustand";
import { persist } from "zustand/middleware";

// ── Smart Fuel Alerts — UI store ─────────────────────────────────────────────
// Open/close state for the Alert Center plus a persisted "last seen" notification
// id. The backend has no read-state, so unread = ids greater than the last one
// the user saw. Persisting it means the unread badge survives reloads.

interface AlertUiState {
  isOpen: boolean;
  /** Highest notification id the user has already seen. */
  lastSeenId: number;
  open: () => void;
  close: () => void;
  /** Mark everything up to `id` as seen (called when the feed is viewed). */
  markSeen: (id: number) => void;
}

export const useAlertUiStore = create<AlertUiState>()(
  persist(
    (set) => ({
      isOpen: false,
      lastSeenId: 0,
      open: () => set({ isOpen: true }),
      close: () => set({ isOpen: false }),
      markSeen: (id) => set((s) => (id > s.lastSeenId ? { lastSeenId: id } : s)),
    }),
    { name: "datafuel-alerts-ui", partialize: (s) => ({ lastSeenId: s.lastSeenId }) },
  ),
);
