import { describe, expect, it } from "vitest";

import type { RecommendationItem } from "@/features/recommendations/types";
import type { SmartAdvice } from "@/features/smart-advice/types";

import { deriveStrategy } from "./strategy";

// Minimal builders — only the fields the engine reads. Defaults make a plain,
// mid-pack station / a neutral "refuel now" verdict; override per case.
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

function advice(overrides: Partial<SmartAdvice>): SmartAdvice {
  return {
    action: "REFUEL_NOW",
    recommended_station: {} as SmartAdvice["recommended_station"],
    current_cost: 50,
    predicted_cost: 50,
    savings_eur: 0,
    savings_pct: 0,
    reasoning: "",
    confidence: 0.85,
    ...overrides,
  };
}

describe("deriveStrategy", () => {
  it("returns null when there is nothing to advise", () => {
    expect(deriveStrategy({ items: [], advice: null })).toBeNull();
  });

  it("advises waiting when the model expects a worthwhile drop", () => {
    const s = deriveStrategy({
      items: [item({ total_cost: 50 })],
      advice: advice({ action: "WAIT", savings_eur: 2, savings_pct: 0.8 }),
    });
    expect(s?.action).toBe("WAIT");
    expect(s?.tone).toBe("wait");
    expect(s?.headline).toBe("Espera unos días");
    expect(s?.reasons.some((r) => r.kind === "price-down")).toBe(true);
  });

  it("escalates to AVOID_TODAY on a notable predicted drop", () => {
    const s = deriveStrategy({
      items: [item({})],
      advice: advice({ action: "WAIT", savings_eur: 3, savings_pct: 2.0 }),
    });
    expect(s?.action).toBe("AVOID_TODAY");
    expect(s?.headline).toBe("Evita repostar hoy");
  });

  it("ignores a trivial waiting saving and refuels today", () => {
    const s = deriveStrategy({
      items: [item({})],
      advice: advice({ action: "WAIT", savings_eur: 0.2, savings_pct: 0.1 }),
    });
    expect(s?.action).toBe("REFUEL_TODAY");
    expect(s?.tone).toBe("go");
  });

  it("recommends visiting a specific station when savings beat the trip", () => {
    // avg total = 50; best is 40 → savingsVsAvg = 10 > travel_cost 5 → detour worth it.
    const s = deriveStrategy({
      items: [
        item({ station_id: 1, brand: "Ballenoil", total_cost: 40, travel_cost: 5 }),
        item({ station_id: 2, total_cost: 60 }),
      ],
      advice: null,
    });
    expect(s?.action).toBe("GO_TO_STATION");
    expect(s?.headline).toBe("Reposta en Ballenoil");
    expect(s?.station?.brand).toBe("Ballenoil");
  });

  it("surfaces a rising-price reason on a REFUEL_NOW verdict", () => {
    const s = deriveStrategy({
      items: [item({})],
      advice: advice({ action: "REFUEL_NOW", savings_eur: -1.0, savings_pct: -0.9 }),
    });
    expect(s?.reasons.some((r) => r.kind === "price-up")).toBe(true);
  });

  it("translates the lowest-total signal into a plain reason", () => {
    const s = deriveStrategy({
      items: [
        item({ station_id: 1, total_cost: 40 }),
        item({ station_id: 2, total_cost: 55 }),
      ],
      advice: null,
    });
    expect(s?.reasons.some((r) => r.kind === "cost")).toBe(true);
  });

  it("reports both grounded forecast figures and never fabricates", () => {
    // avg 50, best 40 → today saves 10; waiting adds 1.5 (backend).
    const withBoth = deriveStrategy({
      items: [item({ total_cost: 40 }), item({ station_id: 2, total_cost: 60 })],
      advice: advice({ action: "WAIT", savings_eur: 1.5, savings_pct: 0.9 }),
    });
    expect(withBoth?.forecast.today).toBeCloseTo(10, 5);
    expect(withBoth?.forecast.waiting).toBeCloseTo(1.5, 5);

    // Single result, no prediction → no fabricated savings.
    const none = deriveStrategy({ items: [item({})], advice: null });
    expect(none?.forecast.today).toBeNull();
    expect(none?.forecast.waiting).toBeNull();
  });

  it("caps reasons and passes through model confidence", () => {
    const s = deriveStrategy({
      items: [item({})],
      advice: advice({ confidence: 0.62 }),
    });
    expect(s?.reasons.length).toBeLessThanOrEqual(4);
    expect(s?.confidence).toBe(0.62);
  });

  it("has null confidence when no prediction is available", () => {
    const s = deriveStrategy({ items: [item({})], advice: null });
    expect(s?.confidence).toBeNull();
  });
});
