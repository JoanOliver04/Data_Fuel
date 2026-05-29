import { describe, expect, it } from "vitest";

import { deriveStationInsights } from "./insights";
import type { RecommendationItem } from "./types";

// Minimal builder — only the fields the engine reads. Defaults make a plain,
// mid-pack station; override per case.
function item(overrides: Partial<RecommendationItem>): RecommendationItem {
  return {
    station_id: 1,
    total_cost: 50,
    price_per_liter: 1.5,
    distance_km: 5,
    fuel_cost: 45,
    travel_cost: 5,
    ...overrides,
  } as RecommendationItem;
}

function ids(badges: { id: string }[]): string[] {
  return badges.map((b) => b.id);
}

describe("deriveStationInsights", () => {
  it("flags the top item as best and computes savings vs the most expensive", () => {
    const [a, b] = deriveStationInsights([
      item({ station_id: 1, total_cost: 40 }),
      item({ station_id: 2, total_cost: 50 }),
    ]);
    expect(a!.isBest).toBe(true);
    expect(b!.isBest).toBe(false);
    expect(a!.savings).toBeCloseTo(10, 5); // 50 - 40
    expect(a!.badges.find((x) => x.id === "best")).toBeDefined();
  });

  it("awards lowest-total and cheapest-fuel only to the matching stations", () => {
    const [cheapTotal, cheapFuel] = deriveStationInsights([
      item({ station_id: 1, total_cost: 40, price_per_liter: 1.6 }),
      item({ station_id: 2, total_cost: 55, price_per_liter: 1.4 }),
    ]);
    expect(ids(cheapTotal!.badges)).toContain("lowest-total");
    expect(ids(cheapTotal!.badges)).not.toContain("cheapest-fuel");
    expect(ids(cheapFuel!.badges)).toContain("cheapest-fuel");
    expect(ids(cheapFuel!.badges)).not.toContain("lowest-total");
  });

  it("never fabricates savings or comparison badges for a single result", () => {
    const [only] = deriveStationInsights([item({ total_cost: 42 })]);
    expect(only!.savings).toBeNull();
    expect(only!.savingsVsAvg).toBeNull();
    // Single result: only `best` is meaningful, comparison badges suppressed.
    expect(ids(only!.badges)).toEqual(["best"]);
  });

  it("marks the smart badge only when an optimization profile drove the ranking", () => {
    const [withProfile] = deriveStationInsights([
      item({ station_id: 1, total_cost: 40, optimization_profile: "BALANCED" }),
      item({ station_id: 2, total_cost: 50 }),
    ]);
    expect(ids(withProfile!.badges)).toContain("smart");

    const [withoutProfile] = deriveStationInsights([
      item({ station_id: 1, total_cost: 40 }),
      item({ station_id: 2, total_cost: 50 }),
    ]);
    expect(ids(withoutProfile!.badges)).not.toContain("smart");
  });

  it("awards traffic-optimized only when peers are actually congested", () => {
    // index 0 is the cheap-but-congested winner; index 1 is the clear route.
    const [congested, clear] = deriveStationInsights([
      item({ station_id: 1, total_cost: 40, price_per_liter: 1.4, distance_km: 3, traffic_delay_seconds: 600 }),
      item({ station_id: 2, total_cost: 50, price_per_liter: 1.5, distance_km: 8, traffic_delay_seconds: 0 }),
    ]);
    expect(ids(clear!.badges)).toContain("traffic-optimized");
    expect(ids(congested!.badges)).not.toContain("traffic-optimized");

    // No congestion anywhere → no traffic badge at all.
    const [a, b] = deriveStationInsights([
      item({ station_id: 1, total_cost: 40, traffic_delay_seconds: 10 }),
      item({ station_id: 2, total_cost: 50, traffic_delay_seconds: 20 }),
    ]);
    expect(ids(a!.badges)).not.toContain("traffic-optimized");
    expect(ids(b!.badges)).not.toContain("traffic-optimized");
  });

  it("prefers driving distance/duration when present for closest & fastest", () => {
    // index 0 wins on cost; index 1 is closer & faster *by road* despite a
    // smaller straight-line km on index 0.
    const [far, near] = deriveStationInsights([
      item({
        station_id: 1,
        total_cost: 40,
        price_per_liter: 1.3,
        distance_km: 1,
        driving_distance_km: 8,
        driving_duration_min: 15,
      }),
      item({
        station_id: 2,
        total_cost: 55,
        price_per_liter: 1.6,
        distance_km: 9,
        driving_distance_km: 2,
        driving_duration_min: 4,
      }),
    ]);
    expect(ids(near!.badges)).toEqual(expect.arrayContaining(["closest", "fastest"]));
    expect(ids(far!.badges)).not.toContain("closest");
    expect(ids(far!.badges)).not.toContain("fastest");
  });

  it("caps badges per card to keep the scan clean", () => {
    const insights = deriveStationInsights([
      item({
        station_id: 1,
        total_cost: 40,
        price_per_liter: 1.4,
        driving_distance_km: 1,
        driving_duration_min: 2,
        optimization_profile: "BALANCED",
        traffic_delay_seconds: 0,
      }),
      item({ station_id: 2, total_cost: 50, traffic_delay_seconds: 600 }),
    ]);
    expect(insights[0]!.badges.length).toBeLessThanOrEqual(3);
  });

  it("frames a savings-vs-time tradeoff for a slower-but-cheaper station", () => {
    // index 0 is fastest (5 min) but pricier; index 1 is 3 min slower yet cheaper.
    const [fast, slowCheap] = deriveStationInsights([
      item({ station_id: 1, total_cost: 55, driving_duration_min: 5 }),
      item({ station_id: 2, total_cost: 50, driving_duration_min: 8 }),
    ]);
    expect(slowCheap!.tradeoff).toBe("Ahorras 5.00 € por solo 3 min más");
    expect(fast!.tradeoff).toBeNull(); // fastest but above average → no spin
  });

  it("celebrates a station that is both fastest and at/under the average", () => {
    const [winner] = deriveStationInsights([
      item({ station_id: 1, total_cost: 40, driving_duration_min: 5 }),
      item({ station_id: 2, total_cost: 60, driving_duration_min: 10 }),
    ]);
    expect(winner!.tradeoff).toBe("Ruta rápida y económica");
  });

  it("produces no tradeoff without driving-time data", () => {
    const [a] = deriveStationInsights([
      item({ station_id: 1, total_cost: 40 }),
      item({ station_id: 2, total_cost: 60 }),
    ]);
    expect(a!.tradeoff).toBeNull();
  });

  it("builds a human-readable rationale for the best station", () => {
    const [best] = deriveStationInsights([
      item({ station_id: 1, total_cost: 40 }),
      item({ station_id: 2, total_cost: 60 }),
    ]);
    expect(best!.reasons.length).toBeGreaterThan(0);
    expect(best!.reasons[0]).toBe("Coste total de repostaje más bajo");
    expect(best!.reasons.some((r) => r.includes("Ahorras"))).toBe(true);
  });
});
