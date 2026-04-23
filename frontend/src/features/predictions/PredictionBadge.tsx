import { usePrediction } from "./hooks";

interface PredictionBadgeProps {
  stationId: number;
  fuelType: string;
}

export function PredictionBadge({ stationId, fuelType }: PredictionBadgeProps) {
  const { data, isLoading } = usePrediction(stationId, fuelType);

  if (isLoading || data === undefined || data === null) return null;

  const { change_pct, advice } = data;
  const isDown = change_pct <= -0.5;
  const isUp = change_pct >= 0.5;

  const colorClass = isDown
    ? "bg-green-100 text-green-700"
    : isUp
      ? "bg-red-100 text-red-700"
      : "bg-gray-100 text-gray-600";

  const arrow = isDown ? "↓" : isUp ? "↑" : "~";

  return (
    <span
      title={advice}
      className={`inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 text-xs font-semibold ${colorClass}`}
    >
      {arrow} {Math.abs(change_pct).toFixed(1)}%
    </span>
  );
}
