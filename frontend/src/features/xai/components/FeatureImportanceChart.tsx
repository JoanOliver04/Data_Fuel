import {
  Bar,
  BarChart,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { FeatureImportanceItem } from "../types";

interface FeatureImportanceChartProps {
  features: FeatureImportanceItem[];
  /** Number of top features to plot (default 10). */
  max?: number;
}

// Violet gradient keyed to rank — the strongest driver is the most saturated.
const BAR_COLORS = [
  "#6d28d9",
  "#7c3aed",
  "#8b5cf6",
  "#9670f0",
  "#a78bfa",
  "#b4a0fb",
  "#c4b5fd",
  "#cdc1fd",
  "#ddd6fe",
  "#e9e3fe",
];

/**
 * Global Random Forest feature importance as an animated, responsive horizontal
 * bar chart (top N, sorted descending). Portfolio-grade analytics styling.
 */
export function FeatureImportanceChart({ features, max = 10 }: FeatureImportanceChartProps) {
  if (features.length === 0) {
    return (
      <p className="py-4 text-center text-xs text-muted-foreground">
        Sin datos de importancia.
      </p>
    );
  }

  const data = features.slice(0, max).map((f) => ({
    name: f.display_name,
    importance: Number(f.importance.toFixed(1)),
    description: f.description,
  }));
  const height = Math.max(160, data.length * 28 + 16);

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart
        layout="vertical"
        data={data}
        margin={{ top: 4, right: 40, bottom: 4, left: 4 }}
        barCategoryGap={6}
      >
        <XAxis type="number" hide domain={[0, "dataMax"]} />
        <YAxis
          type="category"
          dataKey="name"
          width={132}
          tick={{ fontSize: 10 }}
          tickLine={false}
          axisLine={false}
        />
        <Tooltip
          cursor={{ fill: "rgba(139,92,246,0.08)" }}
          formatter={(value: number) => [`${value.toFixed(1)}%`, "Importancia"]}
          labelStyle={{ fontSize: 11 }}
          contentStyle={{ fontSize: 11, borderRadius: 8 }}
        />
        <Bar dataKey="importance" radius={[0, 4, 4, 0]} isAnimationActive>
          {data.map((_, i) => (
            <Cell key={i} fill={BAR_COLORS[i % BAR_COLORS.length]} />
          ))}
          <LabelList
            dataKey="importance"
            position="right"
            formatter={(value: number) => `${value.toFixed(1)}%`}
            style={{ fontSize: 10, fontWeight: 600, fill: "currentColor" }}
          />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
