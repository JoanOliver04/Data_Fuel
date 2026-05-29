import { describe, expect, it } from "vitest";

import { classifyTraffic, getEta } from "./traffic";
import type { RecommendationItem } from "./types";

function item(overrides: Partial<RecommendationItem>): RecommendationItem {
  return { distance_km: 5, ...overrides } as RecommendationItem;
}

describe("classifyTraffic", () => {
  it("returns null when the provider gave no traffic data", () => {
    expect(classifyTraffic(item({ traffic_delay_seconds: null }))).toBeNull();
    expect(classifyTraffic(item({}))).toBeNull();
  });

  it("treats sub-minute delays as free-flow with no delay label", () => {
    const s = classifyTraffic(item({ traffic_delay_seconds: 30 }));
    expect(s?.level).toBe("free");
    expect(s?.delayMinutes).toBe(0);
    expect(s?.delayLabel).toBe("");
    expect(s?.label).toBe("Tráfico optimizado");
  });

  it("classifies by absolute delay on a long trip", () => {
    expect(
      classifyTraffic(item({ traffic_delay_seconds: 120, driving_duration_min: 30 }))?.level,
    ).toBe("light");
    expect(
      classifyTraffic(item({ traffic_delay_seconds: 300, driving_duration_min: 30 }))?.level,
    ).toBe("moderate");
    expect(
      classifyTraffic(item({ traffic_delay_seconds: 600, driving_duration_min: 60 }))?.level,
    ).toBe("heavy");
  });

  it("escalates to heavy on a short trip with a high delay ratio", () => {
    // 2 min delay is "light" in absolute terms, but it doubles a 2-min trip.
    const s = classifyTraffic(item({ traffic_delay_seconds: 120, driving_duration_min: 4 }));
    expect(s?.level).toBe("heavy");
    expect(s?.delayLabel).toBe("+2 min");
  });

  it("falls back to absolute level when duration is unknown", () => {
    expect(
      classifyTraffic(item({ traffic_delay_seconds: 300, driving_duration_min: null }))?.level,
    ).toBe("moderate");
  });
});

describe("getEta", () => {
  it("returns null without any driving duration", () => {
    expect(getEta(item({ driving_duration_min: null, eta_minutes: null }))).toBeNull();
  });

  it("prefers eta_minutes and rounds to whole minutes", () => {
    const e = getEta(item({ eta_minutes: 12.4, driving_duration_min: 30 }));
    expect(e?.durationMin).toBe(12);
    expect(e?.label).toBe("12 min");
  });

  it("falls back to driving_duration_min", () => {
    expect(getEta(item({ driving_duration_min: 8.6 }))?.label).toBe("9 min");
  });

  it("reports road distance when available", () => {
    const e = getEta(item({ eta_minutes: 5, distance_km: 9, driving_distance_km: 2 }));
    expect(e?.distanceKm).toBe(2);
  });
});
