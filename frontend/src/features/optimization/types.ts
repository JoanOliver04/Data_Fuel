/** Multi-objective optimization profile — mirrors the backend StrEnum. */
export type OptimizationProfile = "CHEAPEST" | "BALANCED" | "FASTEST" | "COMMUTER";

export interface ProfileMeta {
  value: OptimizationProfile;
  /** Short label for the segmented control. */
  label: string;
  /** Spanish deterministic rationale (no generative AI). */
  rationale: string;
}

/** Display order + copy for the four profiles. */
export const OPTIMIZATION_PROFILES: readonly ProfileMeta[] = [
  {
    value: "CHEAPEST",
    label: "Económico",
    rationale:
      "Maximiza el ahorro en combustible manteniendo el coste de desplazamiento dentro de lo razonable.",
  },
  {
    value: "BALANCED",
    label: "Equilibrado",
    rationale:
      "Equilibra precio del combustible, distancia y tiempo estimado de llegada.",
  },
  {
    value: "FASTEST",
    label: "Rápido",
    rationale:
      "Minimiza el tiempo total de viaje y evita las rutas congestionadas.",
  },
  {
    value: "COMMUTER",
    label: "Diario",
    rationale:
      "Pensado para el día a día: reduce la exposición al tráfico y el tiempo de viaje.",
  },
] as const;

export const DEFAULT_OPTIMIZATION_PROFILE: OptimizationProfile = "BALANCED";

export function rationaleFor(profile: OptimizationProfile): string {
  return (
    OPTIMIZATION_PROFILES.find((p) => p.value === profile)?.rationale ??
    OPTIMIZATION_PROFILES[1]!.rationale
  );
}
