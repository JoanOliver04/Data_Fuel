import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { PricePoint } from "./types";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("es-ES", { month: "short", day: "numeric" });
}

interface PriceHistoryChartProps {
  data: PricePoint[];
}

export function PriceHistoryChart({ data }: PriceHistoryChartProps) {
  if (data.length === 0) {
    return (
      <p className="py-4 text-center text-xs text-muted-foreground">Sin datos históricos.</p>
    );
  }

  const chartData = data.map((p) => ({ date: formatDate(p.recorded_at), price: p.price }));

  return (
    <ResponsiveContainer width="100%" height={160}>
      <LineChart data={chartData} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey="date" tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
        <YAxis
          tick={{ fontSize: 10 }}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v: number) => v.toFixed(3)}
          domain={["auto", "auto"]}
          width={52}
        />
        <Tooltip
          formatter={(value: number) => [`${value.toFixed(3)} €/L`, "Precio"]}
          labelStyle={{ fontSize: 11 }}
          contentStyle={{ fontSize: 11 }}
        />
        <Line
          type="monotone"
          dataKey="price"
          stroke="#3b82f6"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
