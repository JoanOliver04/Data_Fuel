import { useHealth } from "./hooks";

export function HealthBadge() {
  const { data, isLoading, isError } = useHealth();

  if (isLoading) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border bg-muted/60 px-2.5 py-0.5 text-xs text-muted-foreground">
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-muted-foreground/60" />
        Conectando…
      </span>
    );
  }
  if (isError || !data) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-destructive/30 bg-destructive/10 px-2.5 py-0.5 text-xs text-destructive">
        <span className="h-1.5 w-1.5 rounded-full bg-destructive" />
        Sin conexión
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-xs text-emerald-700 dark:border-emerald-800/40 dark:bg-emerald-950/30 dark:text-emerald-400">
      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
      v{data.version}
    </span>
  );
}
