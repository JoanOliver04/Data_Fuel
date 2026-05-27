import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ShapImpactList } from "../ShapImpactList";
import type { ShapFactor } from "../../types";

const FACTORS: ShapFactor[] = [
  { feature: "precio_semana_anterior", display_name: "Precio de la semana anterior", impact: -0.04, direction: "lowers" },
  { feature: "momentum_7d", display_name: "Momentum de 7 días", impact: -0.02, direction: "lowers" },
  { feature: "mes", display_name: "Mes del año", impact: 0.018, direction: "raises" },
];

describe("ShapImpactList", () => {
  it("renders each factor's label and signed impact", () => {
    render(<ShapImpactList factors={FACTORS} />);
    expect(screen.getByText("Precio de la semana anterior")).toBeInTheDocument();
    expect(screen.getByText("-0.040")).toBeInTheDocument();
    expect(screen.getByText("+0.018")).toBeInTheDocument();
  });

  it("shows an empty state when there are no factors", () => {
    render(<ShapImpactList factors={[]} />);
    expect(screen.getByText(/no disponible/i)).toBeInTheDocument();
  });

  it("caps the number of rendered rows", () => {
    const many: ShapFactor[] = Array.from({ length: 15 }, (_, i) => ({
      feature: `f${i}`,
      display_name: `Factor ${i}`,
      impact: -0.01 * (i + 1),
      direction: "lowers" as const,
    }));
    render(<ShapImpactList factors={many} max={5} />);
    expect(screen.getAllByRole("listitem")).toHaveLength(5);
  });

  it("colors price-raising factors red and price-lowering green", () => {
    render(<ShapImpactList factors={FACTORS} />);
    const lowering = screen.getByText("-0.040");
    const raising = screen.getByText("+0.018");
    expect(lowering.className).toMatch(/emerald/);
    expect(raising.className).toMatch(/red/);
  });
});
