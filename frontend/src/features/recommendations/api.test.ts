import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchRecommendations } from "./api";
import type { RecommendationItem } from "./types";

const mockItem: RecommendationItem = {
  station_id: 1,
  brand: "REPSOL",
  address: "Calle X",
  locality: "Valencia",
  municipality: "Valencia",
  province: "Valencia",
  latitude: 39.47,
  longitude: -0.376,
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

vi.mock("@/lib/api-client", () => ({
  apiFetch: vi.fn(),
}));

afterEach(() => vi.resetAllMocks());

describe("fetchRecommendations", () => {
  it("calls the correct endpoint with required params", async () => {
    const { apiFetch } = await import("@/lib/api-client");
    vi.mocked(apiFetch).mockResolvedValue([mockItem]);

    await fetchRecommendations({ lat: 39.47, lon: -0.376, liters: 40, fuel_type: "gasoil" });

    expect(vi.mocked(apiFetch)).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/recommendations"),
    );
    const calledUrl = vi.mocked(apiFetch).mock.calls[0]![0] as string;
    expect(calledUrl).toContain("lat=39.47");
    expect(calledUrl).toContain("lon=-0.376");
    expect(calledUrl).toContain("liters=40");
    expect(calledUrl).toContain("fuel_type=gasoil");
  });

  it("includes optional params when provided", async () => {
    const { apiFetch } = await import("@/lib/api-client");
    vi.mocked(apiFetch).mockResolvedValue([mockItem]);

    await fetchRecommendations({
      lat: 39.47,
      lon: -0.376,
      liters: 40,
      fuel_type: "gasoil",
      km_cost: 0.2,
      max_distance_km: 15,
      limit: 5,
    });

    const calledUrl = vi.mocked(apiFetch).mock.calls[0]![0] as string;
    expect(calledUrl).toContain("km_cost=0.2");
    expect(calledUrl).toContain("max_distance_km=15");
    expect(calledUrl).toContain("limit=5");
  });

  it("includes the optimization profile when provided", async () => {
    const { apiFetch } = await import("@/lib/api-client");
    vi.mocked(apiFetch).mockResolvedValue([mockItem]);

    await fetchRecommendations({
      lat: 39.47,
      lon: -0.376,
      liters: 40,
      fuel_type: "gasoil",
      optimization_profile: "FASTEST",
    });

    const calledUrl = vi.mocked(apiFetch).mock.calls[0]![0] as string;
    expect(calledUrl).toContain("optimization_profile=FASTEST");
  });

  it("omits optional params when undefined", async () => {
    const { apiFetch } = await import("@/lib/api-client");
    vi.mocked(apiFetch).mockResolvedValue([]);

    await fetchRecommendations({ lat: 39.47, lon: -0.376, liters: 40, fuel_type: "gasolina_95" });

    const calledUrl = vi.mocked(apiFetch).mock.calls[0]![0] as string;
    expect(calledUrl).not.toContain("km_cost");
    expect(calledUrl).not.toContain("max_distance_km");
    expect(calledUrl).not.toContain("limit");
  });
});
