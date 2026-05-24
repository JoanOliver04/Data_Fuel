import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useSearchStore } from "@/stores/search.store";
import { useSettingsStore } from "@/stores/settings.store";
import { usePinLocationMode } from "./usePinLocationMode";

beforeEach(() => {
  useSearchStore.setState({ pinModeActive: false, pinLocation: null });
  useSettingsStore.setState({ userLat: null, userLon: null });
  vi.useFakeTimers();
});

afterEach(() => {
  vi.runOnlyPendingTimers();
  vi.useRealTimers();
});

describe("usePinLocationMode", () => {
  it("activates and deactivates pin mode", () => {
    const { result } = renderHook(() => usePinLocationMode());
    expect(result.current.isActive).toBe(false);

    act(() => result.current.toggle());
    expect(result.current.isActive).toBe(true);
    expect(useSearchStore.getState().pinModeActive).toBe(true);

    act(() => result.current.toggle());
    expect(result.current.isActive).toBe(false);
  });

  it("places a marker and updates the pin location", () => {
    const { result } = renderHook(() => usePinLocationMode());

    act(() => result.current.placeAt(39.123456789, -0.376543211));

    expect(result.current.pinLocation).toEqual({ lat: 39.123457, lon: -0.376543 });
    expect(useSearchStore.getState().pinLocation).toEqual({ lat: 39.123457, lon: -0.376543 });
  });

  it("keeps only one pin when clicking again (moves it)", () => {
    const { result } = renderHook(() => usePinLocationMode());

    act(() => result.current.placeAt(39.47, -0.37));
    act(() => result.current.placeAt(40.41, -3.7));

    expect(result.current.pinLocation).toEqual({ lat: 40.41, lon: -3.7 });
  });

  it("commits the coordinate to the location state after the debounce, driving a recommendation refresh", () => {
    const { result } = renderHook(() => usePinLocationMode());

    act(() => result.current.placeAt(39.47, -0.37));
    // Not committed yet — the query key (userLat/userLon) is unchanged.
    expect(useSettingsStore.getState().userLat).toBeNull();

    act(() => vi.advanceTimersByTime(300));
    expect(useSettingsStore.getState().userLat).toBe(39.47);
    expect(useSettingsStore.getState().userLon).toBe(-0.37);
  });

  it("debounces rapid placements into a single location commit", () => {
    const setLocation = vi.fn();
    useSettingsStore.setState({ setLocation });
    const { result } = renderHook(() => usePinLocationMode());

    act(() => result.current.placeAt(39.47, -0.37));
    act(() => vi.advanceTimersByTime(100));
    act(() => result.current.placeAt(40.41, -3.7));
    act(() => vi.advanceTimersByTime(300));

    expect(setLocation).toHaveBeenCalledTimes(1);
    expect(setLocation).toHaveBeenCalledWith(40.41, -3.7);
  });

  it("previews drag coordinates live without committing, then commits on release", () => {
    const setLocation = vi.fn();
    useSettingsStore.setState({ setLocation });
    const { result } = renderHook(() => usePinLocationMode());

    act(() => result.current.placeAt(39.47, -0.37));
    act(() => vi.advanceTimersByTime(300));
    setLocation.mockClear();

    // Dragging updates the displayed coordinate but must not commit.
    act(() => result.current.handleDrag(39.5, -0.4));
    expect(result.current.displayCoords).toEqual({ lat: 39.5, lon: -0.4 });
    expect(result.current.pinLocation).toEqual({ lat: 39.47, lon: -0.37 });
    act(() => vi.advanceTimersByTime(300));
    expect(setLocation).not.toHaveBeenCalled();

    // Releasing commits the final coordinate.
    act(() => result.current.handleDragEnd(39.6, -0.5));
    expect(result.current.pinLocation).toEqual({ lat: 39.6, lon: -0.5 });
    act(() => vi.advanceTimersByTime(300));
    expect(setLocation).toHaveBeenCalledTimes(1);
    expect(setLocation).toHaveBeenCalledWith(39.6, -0.5);
  });
});
