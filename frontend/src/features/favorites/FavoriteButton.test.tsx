import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useSettingsStore } from "@/stores/settings.store";

import { FavoriteButton } from "./FavoriteButton";

vi.mock("@/stores/settings.store");

const mockToggle = vi.fn();

function mockStore(favorites: number[]) {
  const state = { favorites, toggleFavorite: mockToggle };
  vi.mocked(useSettingsStore).mockImplementation(((selector?: (s: unknown) => unknown) =>
    selector ? selector(state) : state) as typeof useSettingsStore);
}

describe("FavoriteButton", () => {
  beforeEach(() => {
    mockToggle.mockReset();
    mockStore([]);
  });

  it("renders with unfavorited aria-label when not in favorites", () => {
    render(<FavoriteButton stationId={1} />);
    expect(screen.getByRole("button", { name: "Añadir a favoritos" })).toBeInTheDocument();
  });

  it("renders with favorited aria-label when in favorites", () => {
    mockStore([1]);
    render(<FavoriteButton stationId={1} />);
    expect(screen.getByRole("button", { name: "Quitar de favoritos" })).toBeInTheDocument();
  });

  it("calls toggleFavorite with stationId on click", () => {
    render(<FavoriteButton stationId={42} />);
    fireEvent.click(screen.getByRole("button"));
    expect(mockToggle).toHaveBeenCalledWith(42);
  });

  it("aria-pressed is false when not favorited", () => {
    render(<FavoriteButton stationId={1} />);
    expect(screen.getByRole("button")).toHaveAttribute("aria-pressed", "false");
  });

  it("aria-pressed is true when favorited", () => {
    mockStore([1]);
    render(<FavoriteButton stationId={1} />);
    expect(screen.getByRole("button")).toHaveAttribute("aria-pressed", "true");
  });
});
