/**
 * Real Cost formula: Cᵢ = (V · Pᵢ) + (Dᵢ · K)
 *   V  = litres to refuel
 *   Pᵢ = station price per litre (€/L)
 *   Dᵢ = distance to station (km)
 *   K  = cost per km (€/km)
 */
export function calcRealCost(
  pricePerLiter: number,
  distanceKm: number,
  liters: number,
  kmCost: number,
): number {
  return liters * pricePerLiter + distanceKm * kmCost;
}
