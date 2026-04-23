import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { Home } from "./Home";

vi.mock("@/lib/api-client", () => ({
  apiFetch: vi.fn().mockResolvedValue({ status: "ok", version: "0.1.0", name: "Data Fuel API" }),
  ApiError: class ApiError extends Error {},
}));

function renderHome() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("Home page", () => {
  it("renders heading", () => {
    renderHome();
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(/Data Fuel/);
  });

  it("renders location section", () => {
    renderHome();
    expect(screen.getByRole("heading", { level: 2, name: /Mi ubicación/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /usar mi ubicación/i })).toBeInTheDocument();
  });

  it("renders search section", () => {
    renderHome();
    expect(screen.getByText(/Búsqueda/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/litros/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/combustible/i)).toBeInTheDocument();
  });

  it("search button is disabled without location", () => {
    renderHome();
    expect(screen.getByRole("button", { name: /buscar/i })).toBeDisabled();
  });

  it("shows hint when location missing", () => {
    renderHome();
    expect(screen.getByText(/Introduce tu ubicación/i)).toBeInTheDocument();
  });
});
