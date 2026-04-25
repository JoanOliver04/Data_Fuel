import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createVehicleProfile,
  deleteVehicleProfile,
  fetchVehicleProfiles,
  updateVehicleProfile,
} from "./api";
import type { VehicleProfileCreate, VehicleProfileUpdate } from "./types";

const QUERY_KEY = ["vehicle-profiles"] as const;

export function useVehicleProfiles() {
  return useQuery({
    queryKey: QUERY_KEY,
    queryFn: fetchVehicleProfiles,
    staleTime: 5 * 60_000,
  });
}

export function useCreateVehicleProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: VehicleProfileCreate) => createVehicleProfile(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: QUERY_KEY }),
  });
}

export function useUpdateVehicleProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: VehicleProfileUpdate }) =>
      updateVehicleProfile(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: QUERY_KEY }),
  });
}

export function useDeleteVehicleProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteVehicleProfile(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: QUERY_KEY }),
  });
}
