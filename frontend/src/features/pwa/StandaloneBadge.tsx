import { Smartphone } from "lucide-react";

import { useStandaloneMode } from "@/features/pwa/usePWA";
import { cn } from "@/lib/utils";

interface StandaloneBadgeProps {
  className?: string;
}

export function StandaloneBadge({ className }: StandaloneBadgeProps) {
  const standalone = useStandaloneMode();
  if (!standalone) return null;

  return (
    <span
      title="Ejecutándose como app instalada"
      className={cn(
        "inline-flex items-center gap-1 rounded-full border border-primary/20 bg-primary/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-primary",
        className,
      )}
    >
      <Smartphone className="h-3 w-3" />
      App
    </span>
  );
}
