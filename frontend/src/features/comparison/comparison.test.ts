import { describe, expect, it } from "vitest";

import type { RecommendationItem } from "@/features/recommendations/types";

import { compareStations } from "./comparison";

function item(overrides: Partial<RecommendationItem>): RecommendationItem {
  return {
    station_id: 1,
    brand: "Repsol",
    locality: "Alzira",
    total_cost: 50,
    price_per_liter: 1.5,
    distance_km: 5,
    fuel_cost: 45,
    travel_cost: 5,
    ...overrides,
  } as RecommendationItem;
}

function rowById(result: ReturnType<typeof compareStations>, id: string) {
  return result.rows.find((r) => r.metricId === id)!;
}

describe("compareStations", () => {
  it("flags the cheapest fuel and the best total cost on the right columns", () => {
    const result = compareStations([
      item({ station_id: 1, brand: "A", total_cost: 40, price_per_liter: 1.6 }),
      item({ station_id: 2, brand: "B", total_cost: 55, price_per_liter: 1.4 }),
    ]);
    const price = rowById(result, "price");
    const total = rowById(result, "total");
    expect(price.cells[1]!.isWinner).toBe(true); // B cheaper fuel
    expect(price.cells[0]!.isWinner).toBe(false);
    expect(total.cells[0]!.isWinner).toBe(true); // A cheaper total
    expect(result.columns[0]!.awards.map((a) => a.metricId)).toContain("total");
    expect(result.columns[1]!.awards.map((a) => a.metricId)).toContain("price");
  });

  it("awards 'fastest' using driving ETA when available", () => {
    const result = compareStations([
      item({ station_id: 1, brand: "A", driving_duration_min: 12 }),
      item({ station_id: 2, brand: "B", driving_duration_min: 5 }),
    ]);
    const eta = rowById(result, "eta");
    expect(eta.cells[1]!.isWinner).toBe(true);
    expect(eta.cells[0]!.isWinner).toBe(false);
  });

  it("does not award a metric when fewer than two stations carry the data", () => {
    const result = compareStations([
      item({ station_id: 1, brand: "A", optimization_score: 42 }),
      item({ station_id: 2, brand: "B" }), // no score
    ]);
    const score = rowById(result, "score");
    expect(score.cells.every((c) => c.isWinner === false)).toBe(true);
  });

  it("drops a non-differentiating metric where everyone ties", () => {
    const result = compareStations([
      item({ station_id: 1, brand: "A", price_per_liter: 1.5 }),
      item({ station_id: 2, brand: "B", price_per_liter: 1.5 }),
    ]);
    const price = rowById(result, "price");
    expect(price.cells.every((c) => c.isWinner === false)).toBe(true);
  });

  it("produces compact, data-driven insights", () => {
    const result = compareStations([
      item({ station_id: 1, brand: "A", total_cost: 40, driving_duration_min: 5 }),
      item({ station_id: 2, brand: "B", total_cost: 50, driving_duration_min: 12 }),
    ]);
    expect(result.insights.some((i) => i.includes("más barata en total"))).toBe(true);
    expect(result.insights.some((i) => i.includes("min de conducción"))).toBe(true);
    expect(result.insights.length).toBeLessThanOrEqual(3);
  });

  it("summary contrasts cheapest fuel with the best overall value", () => {
    // B has cheaper fuel but A wins the optimization score → A is best overall.
    const result = compareStations([
      item({ station_id: 1, brand: "Alfa", price_per_liter: 1.6, optimization_score: 40, total_cost: 50 }),
      item({ station_id: 2, brand: "Beta", price_per_liter: 1.4, optimization_score: 48, total_cost: 52 }),
    ]);
    expect(result.summary).toContain("Beta"); // cheapest fuel
    expect(result.summary).toContain("Alfa"); // best overall
    expect(result.summary.toLowerCase()).toContain("mejor opción");
  });

  it("never fabricates a summary for a single station", () => {
    const result = compareStations([item({ station_id: 1 })]);
    expect(result.summary).toBe("");
    expect(result.insights).toEqual([]);
  });
});
