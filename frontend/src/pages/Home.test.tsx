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
  it("renders heading and current settings", () => {
    renderHome();

    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(/Data Fuel/);
    expect(screen.getByText(/Coste por km/)).toBeInTheDocument();
  });

  it("shows demo button", () => {
    renderHome();

    expect(screen.getByRole("button", { name: /sumar 5 l/i })).toBeInTheDocument();
  });
});
