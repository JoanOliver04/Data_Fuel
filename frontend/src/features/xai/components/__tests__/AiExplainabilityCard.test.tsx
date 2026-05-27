import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AiExplainabilityCard } from "../AiExplainabilityCard";
import { fetchXaiExplanation } from "../../api";
import type { ExplainRecommendationRequest, ExplainRecommendationResponse } from "../../types";

vi.mock("../../api", () => ({
  fetchXaiExplanation: vi.fn(),
  fetchGlobalFeatureImportance: vi.fn(),
}));

const mockFetch = vi.mocked(fetchXaiExplanation);

beforeEach(() => {
  mockFetch.mockReset();
});

function wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      {children}
    </QueryClientProvider>
  );
}

const PARAMS: ExplainRecommendationRequest = {
  lat: 39.47,
  lon: -0.38,
  fuel_type: "gasolina_95",
  municipio: "Valencia",
  station_lat: 39.45,
  station_lon: -0.39,
  precio_actual: 1.529,
};

const RESPONSE: ExplainRecommendationResponse = {
  veredicto: "ESPERA",
  prediction: 1.49,
  base_value: 1.51,
  precio_actual: 1.529,
  variacion_pct: -2.5,
  confidence: 0.85,
  reasoning: "Data Fuel prevé que el precio bajará.\n- el precio de la semana pasada venía a la baja.",
  shap_available: true,
  top_positive_factors: [
    { feature: "precio_semana_anterior", display_name: "Precio de la semana anterior", impact: -0.04, direction: "lowers" },
  ],
  top_negative_factors: [],
  feature_importance_local: [
    { feature: "precio_semana_anterior", display_name: "Precio de la semana anterior", impact: -0.04, direction: "lowers" },
  ],
  feature_importance_global: [
    { feature: "precio_semana_anterior", display_name: "Precio de la semana anterior", description: "d", importance: 32.9 },
  ],
};

describe("AiExplainabilityCard", () => {
  it("shows a loading skeleton while fetching", () => {
    mockFetch.mockImplementation(() => new Promise(() => {}));
    render(<AiExplainabilityCard params={PARAMS} />, { wrapper });
    expect(screen.getByLabelText(/generando explicaci/i)).toBeInTheDocument();
  });

  it("renders reasoning, verdict and SHAP factors on success", async () => {
    mockFetch.mockResolvedValue(RESPONSE);

    render(<AiExplainabilityCard params={PARAMS} />, { wrapper });

    expect(await screen.findByText("ESPERA")).toBeInTheDocument();
    expect(screen.getByText(/Factores de esta predicción/i)).toBeInTheDocument();
    expect(screen.getByText("Precio de la semana anterior")).toBeInTheDocument();
    expect(screen.getByText(/base 1.510/)).toBeInTheDocument();
  });

  it("shows the degraded notice when SHAP is unavailable", async () => {
    mockFetch.mockResolvedValue({
      ...RESPONSE,
      shap_available: false,
      feature_importance_local: [],
      top_positive_factors: [],
      reasoning: "El desglose por factor no está disponible.",
    });

    render(<AiExplainabilityCard params={PARAMS} />, { wrapper });
    expect(await screen.findByText(/Desglose SHAP no disponible/i)).toBeInTheDocument();
  });

  it("shows an error notice on failure", async () => {
    mockFetch.mockRejectedValue(new Error("503"));

    render(<AiExplainabilityCard params={PARAMS} />, { wrapper });
    expect(await screen.findByText(/no se pudo generar la explicaci/i)).toBeInTheDocument();
  });
});
