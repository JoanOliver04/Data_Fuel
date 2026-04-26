import { describe, expect, it } from "vitest";

import { priceColor } from "./priceColor";

const GREEN = "#22c55e";
const AMBER = "#f59e0b";
const RED = "#ef4444";

describe("priceColor", () => {
  it("paints the cheapest-end values green", () => {
    expect(priceColor(0)).toBe(GREEN);
    expect(priceColor(0.1)).toBe(GREEN);
    expect(priceColor(0.33)).toBe(GREEN);
  });

  it("paints the mid range amber", () => {
    expect(priceColor(0.34)).toBe(AMBER);
    expect(priceColor(0.5)).toBe(AMBER);
    expect(priceColor(0.66)).toBe(AMBER);
  });

  it("paints the most-expensive end red", () => {
    expect(priceColor(0.67)).toBe(RED);
    expect(priceColor(1)).toBe(RED);
  });

  it("clamps out-of-range inputs", () => {
    expect(priceColor(-0.5)).toBe(GREEN);
    expect(priceColor(2)).toBe(RED);
  });
});
