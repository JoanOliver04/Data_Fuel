import { apiFetch } from "@/lib/api-client";

import type { SmartAdvice, SmartAdviceParams } from "./types";

export function fetchSmartAdvice(params: SmartAdviceParams): Promise<SmartAdvice> {
  const qs = new URLSearchParams({
    lat: String(params.lat),
    lon: String(params.lon),
    fuel_type: params.fuel_type,
  });
  if (params.liters !== undefined) qs.set("liters", String(params.liters));
  if (params.km_cost !== undefined) qs.set("km_cost", String(params.km_cost));

  return apiFetch<SmartAdvice>(`/api/v1/smart-advice?${qs}`);
}
