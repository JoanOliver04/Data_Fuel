import { describe, expect, it } from "vitest";

import { calcRealCost } from "./simulatorUtils";

describe("calcRealCost", () => {
  it("computes Ci = (V · Pi) + (Di · K)", () => {
    // 40 L × 1.50 €/L  +  5 km × 0.10 €/km  =  60.50
    expect(calcRealCost(1.5, 5, 40, 0.1)).toBeCloseTo(60.5);
  });

  it("0 litres → only travel cost", () => {
    // 0 × 1.5  +  5 × 0.20  =  1.0
    expect(calcRealCost(1.5, 5, 0, 0.2)).toBeCloseTo(1.0);
  });

  it("0 distance → only fuel cost", () => {
    // 40 × 1.5  +  0 × 0.20  =  60.0
    expect(calcRealCost(1.5, 0, 40, 0.2)).toBeCloseTo(60.0);
  });

  it("0 litres and 0 distance → 0", () => {
    expect(calcRealCost(1.5, 0, 0, 0.2)).toBe(0);
  });

  it("zero price and zero km cost → 0 regardless of volumes", () => {
    expect(calcRealCost(0, 10, 50, 0)).toBe(0);
  });

  it("matches the full formula with realistic values", () => {
    const expected = 35 * 1.459 + 2.3 * 0.13;
    expect(calcRealCost(1.459, 2.3, 35, 0.13)).toBeCloseTo(expected);
  });
});
