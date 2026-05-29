import { Map, Moon, Satellite } from "lucide-react";

import { cn } from "@/lib/utils";
import { MAP_STYLE_LABELS, type MapStyle } from "@/features/map/tiles";

const STYLE_ORDER: MapStyle[] = ["street", "dark", "satellite"];

const STYLE_ICONS: Record<MapStyle, React.ReactNode> = {
  street: <Map className="h-3.5 w-3.5" />,
  dark: <Moon className="h-3.5 w-3.5" />,
  satellite: <Satellite className="h-3.5 w-3.5" />,
};

interface MapStyleSelectorProps {
  value: MapStyle;
  onChange: (style: MapStyle) => void;
  className?: string;
}

export function MapStyleSelector({ value, onChange, className }: MapStyleSelectorProps) {
  return (
    <div
      className={cn(
        "flex flex-col gap-0.5 rounded-xl bg-background/95 p-1 shadow-elevation-lg ring-1 ring-border backdrop-blur-sm",
        className,
      )}
      role="group"
      aria-label="Estilo del mapa"
    >
      {STYLE_ORDER.map((style) => (
        <button
          key={style}
          type="button"
          onClick={() => onChange(style)}
          aria-pressed={value === style}
          aria-label={MAP_STYLE_LABELS[style]}
          className={cn(
            "flex min-h-[44px] min-w-[44px] flex-col items-center justify-center gap-0.5 rounded-lg px-2 py-1.5 text-[10px] font-medium transition-all",
            value === style
              ? "bg-primary text-primary-foreground shadow-sm"
              : "text-muted-foreground hover:bg-accent hover:text-foreground",
          )}
        >
          {STYLE_ICONS[style]}
          <span className="leading-none">{MAP_STYLE_LABELS[style]}</span>
        </button>
      ))}
    </div>
  );
}
