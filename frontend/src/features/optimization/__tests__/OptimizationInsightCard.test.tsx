import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { RecommendationItem } from "@/features/recommendations/types";

import { OptimizationInsightCard } from "../OptimizationInsightCard";

function item(overrides: Partial<RecommendationItem>): RecommendationItem {
  return {
    station_id: 1,
    brand: "TEST",
    address: "a",
    locality: "l",
    municipality: "m",
    province: "p",
    latitude: 39,
    longitude: -0.4,
    schedule: "24H",
    fuel_type: "gasolina_95",
    price_per_liter: 1.5,
    liters: 40,
    distance_km: 3,
    km_cost: 0.13,
    fuel_cost: 60,
    travel_cost: 0.4,
    total_cost: 60.4,
    ...overrides,
  };
}

describe("OptimizationInsightCard", () => {
  it("renders nothing when items are undefined", () => {
    const { container } = render(<OptimizationInsightCard items={undefined} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing when the top item has no profile", () => {
    const { container } = render(<OptimizationInsightCard items={[item({})]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("shows the profile rationale and savings vs runner-up", () => {
    const items = [
      item({ optimization_profile: "FASTEST", optimization_score: 10, eta_minutes: 5, traffic_delay_seconds: 120 }),
      item({ station_id: 2, optimization_profile: "FASTEST", optimization_score: 12 }),
    ];
    render(<OptimizationInsightCard items={items} />);
    expect(screen.getByText(/Rápido/)).toBeInTheDocument();
    expect(screen.getByText(/congestionadas/)).toBeInTheDocument();
    expect(screen.getByText(/5 min/)).toBeInTheDocument();
    expect(screen.getByText(/2.00 € vs/)).toBeInTheDocument(); // 12 - 10
  });

  it("omits savings when there is no runner-up", () => {
    const items = [item({ optimization_profile: "CHEAPEST", optimization_score: 10 })];
    render(<OptimizationInsightCard items={items} />);
    expect(screen.queryByText(/vs\. 2ª/)).not.toBeInTheDocument();
  });
});
