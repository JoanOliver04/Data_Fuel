import { render, screen } from "@testing-library/react";
import React from "react";
import { describe, expect, it, vi } from "vitest";

import { StationMap } from "./StationMap";
import type { RecommendationItem } from "./types";

vi.mock("react-leaflet", () => ({
  MapContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="map-container">{children}</div>
  ),
  TileLayer: () => null,
  CircleMarker: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="user-marker">{children}</div>
  ),
  Marker: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="station-marker">{children}</div>
  ),
  Popup: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  useMap: () => ({ fitBounds: vi.fn() }),
}));

vi.mock("leaflet", () => ({
  divIcon: vi.fn().mockReturnValue({}),
  latLngBounds: vi.fn().mockReturnValue({}),
}));

vi.mock("leaflet/dist/leaflet.css", () => ({}));

const mockItem: RecommendationItem = {
  station_id: 1,
  brand: "REPSOL",
  address: "Calle X",
  locality: "Valencia",
  municipality: "Valencia",
  province: "Valencia",
  latitude: 39.48,
  longitude: -0.37,
  schedule: "L-D: 24H",
  fuel_type: "gasoil",
  price_per_liter: 1.489,
  liters: 40,
  distance_km: 0.5,
  km_cost: 0.13,
  fuel_cost: 59.56,
  travel_cost: 0.065,
  total_cost: 59.625,
};

describe("StationMap", () => {
  it("renders map container", () => {
    render(<StationMap items={[mockItem]} userLat={39.47} userLon={-0.376} />);
    expect(screen.getByTestId("map-container")).toBeInTheDocument();
  });

  it("renders one station marker per item", () => {
    const items = [mockItem, { ...mockItem, station_id: 2 }];
    render(<StationMap items={items} userLat={39.47} userLon={-0.376} />);
    expect(screen.getAllByTestId("station-marker")).toHaveLength(2);
  });

  it("shows station brand and address in popup", () => {
    render(<StationMap items={[mockItem]} userLat={39.47} userLon={-0.376} />);
    expect(screen.getByText("REPSOL")).toBeInTheDocument();
    expect(screen.getByText("Calle X")).toBeInTheDocument();
  });

  it("renders user location marker", () => {
    render(<StationMap items={[mockItem]} userLat={39.47} userLon={-0.376} />);
    expect(screen.getByTestId("user-marker")).toBeInTheDocument();
  });

  it("shows total cost in station popup", () => {
    render(<StationMap items={[mockItem]} userLat={39.47} userLon={-0.376} />);
    expect(screen.getByText("59.63 €")).toBeInTheDocument();
  });
});
