import { MousePointerClick } from "lucide-react";

import type { PinLocation } from "@/stores/search.store";
import { cn } from "@/lib/utils";

interface PinLocationHintProps {
  /** Current coordinate to echo back (live while dragging), if any. */
  coords: PinLocation | null;
  className?: string;
}

/**
 * Subtle helper banner shown while pin mode is active. Echoes the live
 * coordinate during drag so the user gets immediate feedback. Announced
 * politely for assistive tech; entrance animation gates on `motion-safe`.
 */
export function PinLocationHint({ coords, className }: PinLocationHintProps) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        "pointer-events-none flex items-center gap-2 rounded-full px-3.5 py-2",
        "bg-background/95 text-xs font-medium text-foreground shadow-elevation-lg ring-1 ring-border backdrop-blur-sm",
        "motion-safe:animate-in motion-safe:fade-in-0 motion-safe:slide-in-from-top-2",
        className,
      )}
    >
      <MousePointerClick className="h-4 w-4 shrink-0 text-primary" />
      {coords ? (
        <span className="tabular-nums">
          {coords.lat.toFixed(5)}, {coords.lon.toFixed(5)}
        </span>
      ) : (
        <span>Haz clic en el mapa para seleccionar tu ubicación</span>
      )}
    </div>
  );
}
