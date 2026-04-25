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
    public readonly detail?: unknown,
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
      Accept: "application/json",
      ...(init?.body !== undefined ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });

  if (!response.ok) {
    let detail: unknown;
    let detailText: string | undefined;
    try {
      detail = await response.clone().json();
      const maybeDetail = (detail as { detail?: unknown })?.detail;
      if (typeof maybeDetail === "string") detailText = maybeDetail;
    } catch {
      try {
        detailText = await response.text();
      } catch {
        // ignore — body unavailable
      }
    }
    const base = `Request failed: ${response.status} ${response.statusText}`;
    throw new ApiError(response.status, detailText ? `${base} — ${detailText}` : base, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}
