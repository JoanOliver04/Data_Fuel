import { describe, expect, it } from "vitest";

import {
  DEFAULT_OPTIMIZATION_PROFILE,
  OPTIMIZATION_PROFILES,
  rationaleFor,
} from "../types";

describe("optimization types", () => {
  it("exposes the four profiles in order", () => {
    expect(OPTIMIZATION_PROFILES.map((p) => p.value)).toEqual([
      "CHEAPEST",
      "BALANCED",
      "FASTEST",
      "COMMUTER",
    ]);
  });

  it("defaults to BALANCED", () => {
    expect(DEFAULT_OPTIMIZATION_PROFILE).toBe("BALANCED");
  });

  it("every profile has a non-empty label and rationale", () => {
    for (const p of OPTIMIZATION_PROFILES) {
      expect(p.label.length).toBeGreaterThan(0);
      expect(p.rationale.length).toBeGreaterThan(0);
    }
  });

  it("rationaleFor returns the matching rationale", () => {
    expect(rationaleFor("FASTEST")).toBe(
      OPTIMIZATION_PROFILES.find((p) => p.value === "FASTEST")!.rationale,
    );
  });
});
