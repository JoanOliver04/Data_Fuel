/**
 * Bottom-left overlay shown only while the heatmap mode is active. Pure
 * presentational — no data dependencies — so it costs nothing to remount.
 */
export function HeatmapLegend() {
  return (
    <div className="absolute bottom-4 left-4 z-[500] rounded-lg bg-background/95 px-3 py-2 shadow-lg ring-1 ring-border backdrop-blur-sm">
      <p className="text-[10px] font-medium text-muted-foreground">
        Cheaper ← → More expensive
      </p>
      <div
        className="mt-1 h-2 w-32 rounded-full"
        style={{
          backgroundImage:
            "linear-gradient(to right, #22c55e 0%, #22c55e 33%, #f59e0b 34%, #f59e0b 66%, #ef4444 67%, #ef4444 100%)",
        }}
      />
    </div>
  );
}
