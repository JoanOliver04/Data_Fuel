import { describe, expect, it } from "vitest";

import type { RecommendationItem } from "./types";
import { formatTrafficDelay, isStationOpenNow } from "./utils";

// formatTrafficDelay only reads traffic_delay_seconds; a partial cast keeps the
// test focused on the unit under test.
function itemWithDelay(seconds: number | null | undefined): RecommendationItem {
  return { traffic_delay_seconds: seconds } as RecommendationItem;
}

describe("formatTrafficDelay", () => {
  it("returns null when there is no traffic data", () => {
    expect(formatTrafficDelay(itemWithDelay(null))).toBeNull();
    expect(formatTrafficDelay(itemWithDelay(undefined))).toBeNull();
  });

  it("returns null at or below the one-minute threshold", () => {
    expect(formatTrafficDelay(itemWithDelay(0))).toBeNull();
    expect(formatTrafficDelay(itemWithDelay(60))).toBeNull();
  });

  it("formats a delay above the threshold in whole minutes", () => {
    expect(formatTrafficDelay(itemWithDelay(61))).toBe("+1 min");
    expect(formatTrafficDelay(itemWithDelay(120))).toBe("+2 min");
    expect(formatTrafficDelay(itemWithDelay(200))).toBe("+3 min");
  });
});

describe("isStationOpenNow", () => {
  // Reference instants (local time): Wed 2026-05-27 12:00, Wed 03:00, Sun 12:00.
  const wedNoon = new Date(2026, 4, 27, 12, 0);
  const wedEarly = new Date(2026, 4, 27, 3, 0);
  const sunNoon = new Date(2026, 4, 31, 12, 0);

  it("treats 24H as always open", () => {
    expect(isStationOpenNow("L-D: 24H", wedNoon)).toBe(true);
    expect(isStationOpenNow("L-D: 24H", wedEarly)).toBe(true);
  });

  it("respects the open window for non-24h stations (the old bug)", () => {
    // Previously hidden because the schedule wasn't "24H" — now correctly open.
    expect(isStationOpenNow("L-D: 06:00-22:00", wedNoon)).toBe(true);
    expect(isStationOpenNow("L-D: 06:00-22:00", wedEarly)).toBe(false);
  });

  it("honours the day-of-week range (X = Wednesday)", () => {
    expect(isStationOpenNow("L-V: 06:00-22:00", wedNoon)).toBe(true);
    expect(isStationOpenNow("L-V: 06:00-22:00", sunNoon)).toBe(false);
    expect(isStationOpenNow("S-D: 09:00-14:00", sunNoon)).toBe(true);
  });

  it("matches the correct segment in a multi-segment schedule", () => {
    const sched = "L-V: 06:00-22:00; S: 07:00-22:00; D: 08:00-14:00";
    expect(isStationOpenNow(sched, sunNoon)).toBe(true); // Sun 12:00 ∈ 08:00-14:00
    expect(isStationOpenNow(sched, new Date(2026, 4, 31, 15, 0))).toBe(false); // Sun 15:00
  });

  it("treats a 00:00 close as midnight", () => {
    expect(isStationOpenNow("L-D: 06:00-00:00", new Date(2026, 4, 27, 23, 0))).toBe(true);
  });

  it("fails open for empty or unparseable schedules", () => {
    expect(isStationOpenNow("", wedNoon)).toBe(true);
    expect(isStationOpenNow("horario incierto", wedNoon)).toBe(true);
  });
});
