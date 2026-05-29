import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useSettingsStore } from "@/stores/settings.store";

import { OptimizationProfileSelector } from "../OptimizationProfileSelector";

vi.mock("@/stores/settings.store");

const mockSet = vi.fn();

function mockStore(active: string) {
  const state = { optimizationProfile: active, setOptimizationProfile: mockSet };
  vi.mocked(useSettingsStore).mockImplementation(((selector?: (s: unknown) => unknown) =>
    selector ? selector(state) : state) as typeof useSettingsStore);
}

describe("OptimizationProfileSelector", () => {
  beforeEach(() => {
    mockSet.mockReset();
    mockStore("BALANCED");
  });

  it("renders four profile options", () => {
    render(<OptimizationProfileSelector />);
    expect(screen.getAllByRole("radio")).toHaveLength(4);
  });

  it("marks the active profile as checked", () => {
    render(<OptimizationProfileSelector />);
    const balanced = screen.getByRole("radio", { name: /Equilibrado/ });
    expect(balanced).toHaveAttribute("aria-checked", "true");
  });

  it("calls setOptimizationProfile on click", () => {
    render(<OptimizationProfileSelector />);
    fireEvent.click(screen.getByRole("radio", { name: /Rápido/ }));
    expect(mockSet).toHaveBeenCalledWith("FASTEST");
  });
});
