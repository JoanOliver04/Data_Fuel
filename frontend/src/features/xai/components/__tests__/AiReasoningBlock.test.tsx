import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AiReasoningBlock } from "../AiReasoningBlock";

const REASONING =
  "Data Fuel prevé que el precio bajará un 2.5% la próxima semana. Conviene esperar, principalmente porque:\n" +
  "- el precio de la semana pasada venía a la baja.\n" +
  "- el momentum semanal es negativo (desacelerando).";

describe("AiReasoningBlock", () => {
  it("renders the verdict chip", () => {
    render(<AiReasoningBlock reasoning={REASONING} veredicto="ESPERA" confidence={0.85} />);
    expect(screen.getByText("ESPERA")).toBeInTheDocument();
  });

  it("renders the confidence percentage", () => {
    render(<AiReasoningBlock reasoning={REASONING} veredicto="ESPERA" confidence={0.85} />);
    expect(screen.getByText("85%")).toBeInTheDocument();
  });

  it("splits the reasoning into a lead and bullet points", () => {
    render(<AiReasoningBlock reasoning={REASONING} veredicto="ESPERA" confidence={0.85} />);
    expect(screen.getByText(/Conviene esperar/)).toBeInTheDocument();
    const bullets = screen.getAllByRole("listitem");
    expect(bullets).toHaveLength(2);
    expect(bullets[0]).toHaveTextContent("el precio de la semana pasada venía a la baja");
  });

  it("clamps out-of-range confidence", () => {
    render(<AiReasoningBlock reasoning="Sin factores claros." veredicto="REPOSTA AHORA" confidence={1.4} />);
    expect(screen.getByText("100%")).toBeInTheDocument();
  });

  it("renders reasoning with no bullets", () => {
    render(<AiReasoningBlock reasoning="Sin factores claros." veredicto="REPOSTA AHORA" confidence={0.5} />);
    expect(screen.getByText("Sin factores claros.")).toBeInTheDocument();
    expect(screen.queryAllByRole("listitem")).toHaveLength(0);
  });
});
