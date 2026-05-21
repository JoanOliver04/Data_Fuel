import { describe, expect, it } from "vitest";

import type { RecommendationItem } from "./types";
import { formatTrafficDelay } from "./utils";

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
