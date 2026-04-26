/**
 * Map a min-max-normalised price (0 = cheapest, 1 = most expensive) to a
 * Tailwind-aligned hex colour on the green → amber → red gradient used by
 * the heatmap layer and its legend.
 */
export function priceColor(normalized: number): string {
  // Clamp first so out-of-spec inputs from the API can't paint a hole.
  const n = Math.max(0, Math.min(1, normalized));
  if (n <= 0.33) return "#22c55e"; // tailwind green-500
  if (n <= 0.66) return "#f59e0b"; // tailwind amber-500
  return "#ef4444"; // tailwind red-500
}
