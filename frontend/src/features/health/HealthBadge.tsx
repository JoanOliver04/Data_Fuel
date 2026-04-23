import { useHealth } from "./hooks";

export function HealthBadge() {
  const { data, isLoading, isError } = useHealth();

  if (isLoading) {
    return <span className="text-muted-foreground text-sm">Comprobando backend…</span>;
  }
  if (isError || !data) {
    return <span className="text-destructive text-sm">Backend no disponible</span>;
  }

  return (
    <span className="text-sm">
      Backend: <span className="font-mono text-green-600">{data.status}</span> · v{data.version}
    </span>
  );
}
