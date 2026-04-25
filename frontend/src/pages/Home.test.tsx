import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { Home } from "./Home";

vi.mock("@/lib/api-client", () => ({
  apiFetch: vi.fn().mockResolvedValue({ status: "ok", version: "0.1.0", name: "Data Fuel API" }),
  ApiError: class ApiError extends Error {},
}));

// Complex child components depend on leaflet / network — stub them out
vi.mock("@/features/map/MapView", () => ({
  MapView: () => <div data-testid="map-view" />,
}));
vi.mock("@/features/search/SearchBar", () => ({
  SearchBar: () => <div data-testid="search-bar" />,
}));
vi.mock("@/features/search/FiltersBar", () => ({
  FiltersBar: () => <div data-testid="filters-bar" />,
}));
vi.mock("@/features/recommendations/StationList", () => ({
  StationList: () => <div data-testid="station-list" />,
}));
vi.mock("@/features/smart-advice/SmartAdviceCard", () => ({
  SmartAdviceCard: () => <div data-testid="smart-advice-card" />,
}));
vi.mock("@/features/health/HealthBadge", () => ({
  HealthBadge: () => <span data-testid="health-badge" />,
}));

function renderHome() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("Home page", () => {
  it("renders app heading", () => {
    renderHome();
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(/Data Fuel/);
  });

  it("renders the search bar", () => {
    renderHome();
    expect(screen.getByTestId("search-bar")).toBeInTheDocument();
  });

  it("renders the filters bar", () => {
    renderHome();
    expect(screen.getByTestId("filters-bar")).toBeInTheDocument();
  });

  it("renders theme toggle button", () => {
    renderHome();
    expect(
      screen.getByRole("button", { name: /cambiar a modo/i }),
    ).toBeInTheDocument();
  });

  it("shows no-location prompt when location is missing", () => {
    renderHome();
    // Text appears in both the sidebar and the map area when no location is set
    const prompts = screen.getAllByText(/Activa la geolocalización/i);
    expect(prompts.length).toBeGreaterThanOrEqual(1);
  });
});
