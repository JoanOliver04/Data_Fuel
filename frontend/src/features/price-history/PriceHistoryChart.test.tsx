import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { PriceHistoryChart } from "./PriceHistoryChart";
import type { PricePoint } from "./types";

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="chart-container">{children}</div>
  ),
  LineChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="line-chart">{children}</div>
  ),
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  Tooltip: () => null,
  CartesianGrid: () => null,
}));

const SAMPLE_DATA: PricePoint[] = [
  { recorded_at: "2024-06-01T10:00:00Z", price: 1.489 },
  { recorded_at: "2024-06-02T10:00:00Z", price: 1.499 },
  { recorded_at: "2024-06-03T10:00:00Z", price: 1.479 },
];

describe("PriceHistoryChart", () => {
  it("shows empty state message when data is empty", () => {
    render(<PriceHistoryChart data={[]} />);
    expect(screen.getByText("Sin datos históricos.")).toBeInTheDocument();
  });

  it("renders chart container when data is provided", () => {
    render(<PriceHistoryChart data={SAMPLE_DATA} />);
    expect(screen.getByTestId("chart-container")).toBeInTheDocument();
  });

  it("renders LineChart when data is provided", () => {
    render(<PriceHistoryChart data={SAMPLE_DATA} />);
    expect(screen.getByTestId("line-chart")).toBeInTheDocument();
  });

  it("does not show empty state when data is provided", () => {
    render(<PriceHistoryChart data={SAMPLE_DATA} />);
    expect(screen.queryByText("Sin datos históricos.")).not.toBeInTheDocument();
  });
});
