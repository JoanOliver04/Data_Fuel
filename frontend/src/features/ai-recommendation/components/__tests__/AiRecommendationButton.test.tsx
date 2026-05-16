import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";

import { AiRecommendationButton } from "../AiRecommendationButton";

// ── Store mock ────────────────────────────────────────────────────────────────

vi.mock("@/stores/settings.store", () => ({
  useSettingsStore: vi.fn(() => ({
    userLat: 39.47,
    userLon: -0.38,
    preferredFuel: "gasolina_95",
  })),
}));

// ── API mock ──────────────────────────────────────────────────────────────────

vi.mock("@/features/ai-recommendation/api", () => ({
  fetchAiRecommendation: vi.fn(),
}));

// ── Wrapper ───────────────────────────────────────────────────────────────────

function wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={new QueryClient({ defaultOptions: { mutations: { retry: false } } })}>
      {children}
    </QueryClientProvider>
  );
}

const DEFAULT_PROPS = {
  municipio: "Valencia",
  comarca: "Horta de València",
  precioActual: 1.529,
  onResult: vi.fn(),
};

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("AiRecommendationButton", () => {
  it("renders idle label", () => {
    render(<AiRecommendationButton {...DEFAULT_PROPS} />, { wrapper });
    expect(screen.getByRole("button", { name: /recomendaci/i })).toBeInTheDocument();
  });

  it("is enabled when location is set", () => {
    render(<AiRecommendationButton {...DEFAULT_PROPS} />, { wrapper });
    expect(screen.getByRole("button")).not.toBeDisabled();
  });

  it("shows loading label after click", async () => {
    const { fetchAiRecommendation } = await import("@/features/ai-recommendation/api");
    vi.mocked(fetchAiRecommendation).mockImplementation(() => new Promise(() => {}));

    render(<AiRecommendationButton {...DEFAULT_PROPS} />, { wrapper });
    await userEvent.click(screen.getByRole("button"));

    expect(await screen.findByText(/analiz/i)).toBeInTheDocument();
    expect(screen.getByRole("button")).toBeDisabled();
  });

  it("calls onResult with API response on success", async () => {
    const mockResult = {
      veredicto: "ESPERA" as const,
      precio_actual: 1.529,
      precio_predicho: 1.469,
      variacion_pct: -3.92,
      advice: "Espera",
      confianza: 0.9,
    };
    const { fetchAiRecommendation } = await import("@/features/ai-recommendation/api");
    vi.mocked(fetchAiRecommendation).mockResolvedValue(mockResult);

    const onResult = vi.fn();
    render(<AiRecommendationButton {...DEFAULT_PROPS} onResult={onResult} />, { wrapper });
    await userEvent.click(screen.getByRole("button"));

    await vi.waitFor(() => {
      expect(onResult).toHaveBeenCalled();
      const [data] = onResult.mock.calls[0]!;
      expect(data).toEqual(mockResult);
    });
  });

  it("shows error message on API failure", async () => {
    const { fetchAiRecommendation } = await import("@/features/ai-recommendation/api");
    vi.mocked(fetchAiRecommendation).mockRejectedValue(new Error("503"));

    render(<AiRecommendationButton {...DEFAULT_PROPS} />, { wrapper });
    await userEvent.click(screen.getByRole("button"));

    expect(await screen.findByText(/no se pudo/i)).toBeInTheDocument();
  });
});

describe("AiRecommendationButton — disabled when no location", () => {
  it("is disabled when location is null", () => {
    vi.doMock("@/stores/settings.store", () => ({
      useSettingsStore: vi.fn(() => ({
        userLat: null,
        userLon: null,
        preferredFuel: "gasolina_95",
      })),
    }));

    render(<AiRecommendationButton {...{ ...DEFAULT_PROPS, precioActual: 0 }} />, { wrapper });
    expect(screen.getByRole("button")).toBeDisabled();
  });
});
