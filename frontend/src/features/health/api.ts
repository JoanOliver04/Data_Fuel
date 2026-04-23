import { apiFetch } from "@/lib/api-client";

export interface HealthResponse {
  status: string;
  version: string;
  name: string;
}

export function fetchHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/api/v1/health");
}
