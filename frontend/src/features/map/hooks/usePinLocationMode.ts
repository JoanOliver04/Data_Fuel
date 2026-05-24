import { useCallback, useEffect, useRef, useState } from "react";

import { useSearchStore, type PinLocation } from "@/stores/search.store";
import { useSettingsStore } from "@/stores/settings.store";

/** Debounce window before a pinned coordinate is committed to the global
 *  location (and therefore the recommendation query). Coalesces rapid clicks /
 *  drag releases into a single state change so we never fire duplicate API
 *  calls. */
const COMMIT_DEBOUNCE_MS = 300;

/** Match the 6-decimal precision the rest of the app stores coordinates with
 *  (see SearchBar / LocationPicker), keeping query keys stable. */
function round6(value: number): number {
  return Math.round(value * 1e6) / 1e6;
}

export interface UsePinLocationMode {
  /** Whether map clicks currently drop/move the pin. */
  isActive: boolean;
  /** The committed manual pin, or null when none is placed. */
  pinLocation: PinLocation | null;
  /** Coordinate to surface in the UI — the live drag position while dragging,
   *  otherwise the committed pin. */
  displayCoords: PinLocation | null;
  /** Toggle pin mode on/off. */
  toggle: () => void;
  /** Place (or move) the pin from a map click. Only one pin ever exists. */
  placeAt: (lat: number, lon: number) => void;
  /** Live drag feedback — updates the displayed coordinate without committing
   *  to the location state (so no recommendation refetch fires mid-drag). */
  handleDrag: (lat: number, lon: number) => void;
  /** Drag released — commit the final coordinate (debounced). */
  handleDragEnd: (lat: number, lon: number) => void;
}

/**
 * Headless orchestration for the interactive "pin location" map mode.
 *
 * Owns no Leaflet APIs so it can be unit-tested in isolation and reused by any
 * map surface. Committing a pin flows through the existing
 * `settingsStore.setLocation`, which means a manual pin behaves exactly like a
 * GPS coordinate change: it updates the search params, triggers the TanStack
 * Query refetch and re-centres the map via the existing `FlyToHandler`.
 *
 * Call this once per map and wire the returned handlers down to the visual
 * components — the shared pin state lives in Zustand, drag preview is local.
 */
export function usePinLocationMode(): UsePinLocationMode {
  const isActive = useSearchStore((s) => s.pinModeActive);
  const pinLocation = useSearchStore((s) => s.pinLocation);
  const setPinModeActive = useSearchStore((s) => s.setPinModeActive);
  const setPinLocation = useSearchStore((s) => s.setPinLocation);
  const setLocation = useSettingsStore((s) => s.setLocation);

  // Transient live position while the marker is being dragged. Kept out of the
  // store (and off the marker's controlled `position`) so dragging stays smooth
  // and never schedules a refetch.
  const [dragCoords, setDragCoords] = useState<PinLocation | null>(null);

  const commitTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const scheduleCommit = useCallback(
    (lat: number, lon: number) => {
      if (commitTimer.current) clearTimeout(commitTimer.current);
      commitTimer.current = setTimeout(() => {
        setLocation(lat, lon);
        commitTimer.current = null;
      }, COMMIT_DEBOUNCE_MS);
    },
    [setLocation],
  );

  // Cancel any in-flight commit if the map unmounts.
  useEffect(
    () => () => {
      if (commitTimer.current) clearTimeout(commitTimer.current);
    },
    [],
  );

  const toggle = useCallback(() => {
    setPinModeActive(!useSearchStore.getState().pinModeActive);
  }, [setPinModeActive]);

  const placeAt = useCallback(
    (lat: number, lon: number) => {
      const next = { lat: round6(lat), lon: round6(lon) };
      setPinLocation(next);
      scheduleCommit(next.lat, next.lon);
    },
    [setPinLocation, scheduleCommit],
  );

  const handleDrag = useCallback((lat: number, lon: number) => {
    setDragCoords({ lat: round6(lat), lon: round6(lon) });
  }, []);

  const handleDragEnd = useCallback(
    (lat: number, lon: number) => {
      const next = { lat: round6(lat), lon: round6(lon) };
      setDragCoords(null);
      setPinLocation(next);
      scheduleCommit(next.lat, next.lon);
    },
    [setPinLocation, scheduleCommit],
  );

  return {
    isActive,
    pinLocation,
    displayCoords: dragCoords ?? pinLocation,
    toggle,
    placeAt,
    handleDrag,
    handleDragEnd,
  };
}
