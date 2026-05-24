import { MapPin } from "lucide-react";

import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

interface PinLocationControlProps {
  active: boolean;
  onToggle: () => void;
  /** Positioning supplied by the host map. */
  className?: string;
}

/**
 * Floating map control that toggles the interactive "pin location" mode.
 * Mirrors the visual language of the existing heatmap toggle.
 */
export function PinLocationControl({ active, onToggle, className }: PinLocationControlProps) {
  return (
    <TooltipProvider delayDuration={300}>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            onClick={onToggle}
            aria-pressed={active}
            aria-label="Seleccionar ubicación exacta"
            className={cn(
              "flex h-9 w-9 items-center justify-center rounded-full shadow-md ring-1 backdrop-blur-sm transition-colors",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
              active
                ? "bg-primary text-primary-foreground ring-primary hover:bg-primary/90"
                : "bg-background/95 text-foreground ring-border hover:bg-background",
              className,
            )}
          >
            <MapPin className="h-4 w-4" />
          </button>
        </TooltipTrigger>
        <TooltipContent side="right">Seleccionar ubicación exacta</TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
