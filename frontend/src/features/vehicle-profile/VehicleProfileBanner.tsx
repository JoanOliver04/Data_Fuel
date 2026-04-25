import { ChevronRight, CarFront } from "lucide-react";
import { Link } from "react-router-dom";

export function VehicleProfileBanner() {
  return (
    <Link
      to="/settings"
      className="flex items-center justify-between gap-2 rounded-lg border border-dashed border-border bg-muted/40 px-3 py-2.5 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
    >
      <span className="flex items-center gap-2">
        <CarFront className="h-4 w-4 shrink-0" />
        Configura tu vehículo para un Coste Real más preciso
      </span>
      <ChevronRight className="h-4 w-4 shrink-0" />
    </Link>
  );
}
