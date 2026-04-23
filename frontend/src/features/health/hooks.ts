import { useQuery } from "@tanstack/react-query";

import { fetchHealth, type HealthResponse } from "./api";

export function useHealth() {
  return useQuery<HealthResponse>({
    queryKey: ["health"],
    queryFn: fetchHealth,
  });
}
