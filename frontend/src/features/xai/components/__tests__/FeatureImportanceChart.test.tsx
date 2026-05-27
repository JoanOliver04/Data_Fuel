import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { FeatureImportanceChart } from "../FeatureImportanceChart";
import type { FeatureImportanceItem } from "../../types";

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="chart-container">{children}</div>
  ),
  BarChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="bar-chart">{children}</div>
  ),
  Bar: ({ children }: { children: React.ReactNode }) => <div data-testid="bar">{children}</div>,
  Cell: () => null,
  LabelList: () => null,
  XAxis: () => null,
  YAxis: () => null,
  Tooltip: () => null,
}));

const FEATURES: FeatureImportanceItem[] = [
  { feature: "precio_semana_anterior", display_name: "Precio de la semana anterior", description: "d", importance: 32.9 },
  { feature: "precio_medio_municipio", display_name: "Precio medio del municipio", description: "d", importance: 25.5 },
];

describe("FeatureImportanceChart", () => {
  it("renders the chart container with data", () => {
    render(<FeatureImportanceChart features={FEATURES} />);
    expect(screen.getByTestId("chart-container")).toBeInTheDocument();
    expect(screen.getByTestId("bar-chart")).toBeInTheDocument();
  });

  it("shows an empty state when there are no features", () => {
    render(<FeatureImportanceChart features={[]} />);
    expect(screen.getByText(/sin datos/i)).toBeInTheDocument();
    expect(screen.queryByTestId("chart-container")).not.toBeInTheDocument();
  });
});
