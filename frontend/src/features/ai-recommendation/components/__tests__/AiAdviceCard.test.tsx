import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AiAdviceCard } from "../AiAdviceCard";
import type { AiRecommendationResponse } from "../../types";

const REPOSTA: AiRecommendationResponse = {
  veredicto: "REPOSTA AHORA",
  precio_actual: 1.529,
  precio_predicho: 1.599,
  variacion_pct: 4.58,
  advice: "Reposta ahora, el precio subirá un 4.6% la próxima semana",
  confianza: 0.95,
};

const ESPERA: AiRecommendationResponse = {
  veredicto: "ESPERA",
  precio_actual: 1.529,
  precio_predicho: 1.469,
  variacion_pct: -3.92,
  advice: "Espera, el precio bajará un 3.9% la próxima semana",
  confianza: 0.78,
};

describe("AiAdviceCard — REPOSTA AHORA", () => {
  it("renders the veredicto", () => {
    render(<AiAdviceCard response={REPOSTA} />);
    expect(screen.getByText("REPOSTA AHORA")).toBeInTheDocument();
  });

  it("shows current and predicted prices", () => {
    render(<AiAdviceCard response={REPOSTA} />);
    expect(screen.getByText(/1\.529/)).toBeInTheDocument();
    expect(screen.getByText(/1\.599/)).toBeInTheDocument();
  });

  it("shows the advice text", () => {
    render(<AiAdviceCard response={REPOSTA} />);
    expect(screen.getByText(/subirá/i)).toBeInTheDocument();
  });

  it("shows confidence as percentage", () => {
    render(<AiAdviceCard response={REPOSTA} />);
    expect(screen.getByText("95%")).toBeInTheDocument();
  });

  it("uses emerald color variant on the outer card", () => {
    const { container } = render(<AiAdviceCard response={REPOSTA} />);
    const card = container.firstChild as HTMLElement;
    expect(card.className).toMatch(/border-emerald-300/);
    expect(card.className).toMatch(/bg-emerald-50/);
    expect(card.className).not.toMatch(/border-amber-300/);
  });

  it("shows the price-up signal in red with a + sign", () => {
    render(<AiAdviceCard response={REPOSTA} />);
    const variation = screen.getByText(/\+4\.6%/);
    expect(variation.className).toMatch(/text-red-600/);
  });
});

describe("AiAdviceCard — ESPERA", () => {
  it("renders the veredicto", () => {
    render(<AiAdviceCard response={ESPERA} />);
    expect(screen.getByText("ESPERA")).toBeInTheDocument();
  });

  it("shows current and predicted prices", () => {
    render(<AiAdviceCard response={ESPERA} />);
    expect(screen.getByText(/1\.529/)).toBeInTheDocument();
    expect(screen.getByText(/1\.469/)).toBeInTheDocument();
  });

  it("shows the advice text", () => {
    render(<AiAdviceCard response={ESPERA} />);
    expect(screen.getByText(/bajará/i)).toBeInTheDocument();
  });

  it("shows confidence as percentage", () => {
    render(<AiAdviceCard response={ESPERA} />);
    expect(screen.getByText("78%")).toBeInTheDocument();
  });

  it("uses amber color variant on the outer card", () => {
    const { container } = render(<AiAdviceCard response={ESPERA} />);
    const card = container.firstChild as HTMLElement;
    expect(card.className).toMatch(/border-amber-300/);
    expect(card.className).toMatch(/bg-amber-50/);
    expect(card.className).not.toMatch(/border-emerald-300/);
  });

  it("shows the price-drop signal in emerald with a - sign", () => {
    render(<AiAdviceCard response={ESPERA} />);
    const variation = screen.getByText(/-3\.9%/);
    expect(variation.className).toMatch(/text-emerald-700/);
  });
});

describe("AiAdviceCard — dismiss", () => {
  it("calls onDismiss when X is clicked", async () => {
    const onDismiss = vi.fn();
    render(<AiAdviceCard response={REPOSTA} onDismiss={onDismiss} />);
    await userEvent.click(screen.getByRole("button", { name: /cerrar/i }));
    expect(onDismiss).toHaveBeenCalledOnce();
  });

  it("does not render dismiss button when onDismiss is not provided", () => {
    render(<AiAdviceCard response={REPOSTA} />);
    expect(screen.queryByRole("button", { name: /cerrar/i })).not.toBeInTheDocument();
  });
});
