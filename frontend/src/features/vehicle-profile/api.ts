import { apiFetch } from "@/lib/api-client";

import type {
  KmCostEstimate,
  VehicleProfile,
  VehicleProfileCreate,
  VehicleProfileUpdate,
} from "./types";

export async function fetchVehicleProfiles(): Promise<VehicleProfile[]> {
  return apiFetch<VehicleProfile[]>("/api/v1/vehicle-profiles");
}

export async function fetchVehicleProfile(id: number): Promise<VehicleProfile> {
  return apiFetch<VehicleProfile>(`/api/v1/vehicle-profiles/${id}`);
}

export async function createVehicleProfile(data: VehicleProfileCreate): Promise<VehicleProfile> {
  return apiFetch<VehicleProfile>("/api/v1/vehicle-profiles", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function updateVehicleProfile(
  id: number,
  data: VehicleProfileUpdate,
): Promise<VehicleProfile> {
  return apiFetch<VehicleProfile>(`/api/v1/vehicle-profiles/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function deleteVehicleProfile(id: number): Promise<void> {
  await apiFetch<void>(`/api/v1/vehicle-profiles/${id}`, { method: "DELETE" });
}

export async function estimateKmCost(
  consumption: number,
  fuelPrice: number,
): Promise<KmCostEstimate> {
  const qs = new URLSearchParams({
    consumption: String(consumption),
    fuel_price: String(fuelPrice),
  });
  return apiFetch<KmCostEstimate>(`/api/v1/vehicle-profiles/estimate-km-cost?${qs}`);
}
