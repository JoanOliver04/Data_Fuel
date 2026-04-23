/**
 * Thin fetch wrapper for the Data Fuel backend.
 *
 * In dev, requests to `/api/*` are proxied to http://localhost:8000 by Vite
 * (see vite.config.ts). In production, set VITE_API_BASE_URL to the absolute
 * backend URL.
 */

const BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? "";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const response = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    throw new ApiError(response.status, `Request failed: ${response.status} ${response.statusText}`);
  }

  return response.json() as Promise<T>;
}
