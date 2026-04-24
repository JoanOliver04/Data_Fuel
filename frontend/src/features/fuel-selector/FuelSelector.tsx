import type { ReactNode } from "react";

import { cn } from "@/lib/utils";
import type { FuelType } from "@/types/fuel";

import { FUEL_GROUPS } from "./fuelTypes";

// ── Tooltip ────────────────────────────────────────────────────────────────

interface TooltipProps {
  text: string;
  children: ReactNode;
}

function Tooltip({ text, children }: TooltipProps) {
  return (
    <div className="group/tip relative inline-block">
      {children}
      <span
        role="tooltip"
        className={cn(
          "pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 -translate-x-1/2",
          "whitespace-nowrap rounded-lg bg-foreground px-2.5 py-1 text-xs text-background shadow-md",
          "opacity-0 transition-opacity duration-150 group-hover/tip:opacity-100",
        )}
      >
        {text}
        {/* Arrow */}
        <span className="absolute left-1/2 top-full -translate-x-1/2 border-4 border-transparent border-t-foreground" />
      </span>
    </div>
  );
}

// ── FuelButton ─────────────────────────────────────────────────────────────

interface FuelButtonProps {
  icon: string;
  shortLabel: string;
  isPremium?: true;
  isSelected: boolean;
  onClick: () => void;
  tooltip: string;
}

function FuelButton({ icon, shortLabel, isPremium, isSelected, onClick, tooltip }: FuelButtonProps) {
  return (
    <Tooltip text={tooltip}>
      <button
        type="button"
        onClick={onClick}
        aria-pressed={isSelected}
        className={cn(
          "relative inline-flex select-none items-center gap-1.5 rounded-xl px-3.5 py-2 text-sm font-medium",
          "transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
          isSelected
            ? [
                "scale-105 bg-primary text-primary-foreground",
                "shadow-[0_0_0_2px_hsl(var(--ring)/0.4),0_2px_8px_hsl(var(--primary)/0.35)]",
              ]
            : "bg-muted text-foreground hover:bg-accent hover:text-accent-foreground active:scale-95",
        )}
      >
        <span aria-hidden="true">{icon}</span>
        {shortLabel}
        {isPremium && (
          <span
            aria-label="premium"
            className="absolute -right-1.5 -top-1.5 text-[11px] leading-none drop-shadow-sm"
          >
            ⭐
          </span>
        )}
      </button>
    </Tooltip>
  );
}

// ── FuelSelector ───────────────────────────────────────────────────────────

export interface FuelSelectorProps {
  value: FuelType;
  onChange: (value: FuelType) => void;
  className?: string;
}

export function FuelSelector({ value, onChange, className }: FuelSelectorProps) {
  return (
    <div className={cn("space-y-3", className)} role="group" aria-label="Selección de combustible">
      {FUEL_GROUPS.map((group) => (
        <div key={group.label}>
          <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            {group.icon} {group.label}
          </p>
          <div className="flex flex-wrap gap-2">
            {group.options.map((option) => (
              <FuelButton
                key={option.value}
                icon={option.icon}
                shortLabel={option.shortLabel}
                isPremium={option.isPremium}
                isSelected={value === option.value}
                onClick={() => onChange(option.value)}
                tooltip={option.tooltip}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
