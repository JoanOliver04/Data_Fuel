import { CheckCircle2, Info, X, XCircle } from "lucide-react";

import { cn } from "@/lib/utils";
import { useToastStore, type Toast } from "@/stores/toast.store";

const VARIANT_CONFIG: Record<
  Toast["variant"],
  { icon: React.ReactNode; className: string }
> = {
  success: {
    icon: <CheckCircle2 className="h-4 w-4 text-emerald-500" aria-hidden />,
    className:
      "border-emerald-200 bg-white text-foreground dark:border-emerald-800/50 dark:bg-card",
  },
  error: {
    icon: <XCircle className="h-4 w-4 text-destructive" aria-hidden />,
    className:
      "border-destructive/30 bg-white text-foreground dark:border-destructive/30 dark:bg-card",
  },
  info: {
    icon: <Info className="h-4 w-4 text-primary" aria-hidden />,
    className: "border-border bg-white text-foreground dark:bg-card",
  },
};

export function Toaster() {
  const toasts = useToastStore((s) => s.toasts);
  const dismiss = useToastStore((s) => s.dismiss);

  return (
    <div
      role="region"
      aria-live="polite"
      aria-label="Notificaciones"
      className="pointer-events-none fixed bottom-6 right-4 z-50 flex flex-col items-end gap-2"
    >
      {toasts.map((t) => {
        const config = VARIANT_CONFIG[t.variant];
        return (
          <div
            key={t.id}
            role="status"
            className={cn(
              "pointer-events-auto flex w-full max-w-[360px] items-start gap-3 rounded-xl border px-4 py-3",
              "shadow-lg shadow-black/5 dark:shadow-black/30",
              "animate-in slide-in-from-right-4 fade-in-0 duration-300",
              config.className,
            )}
          >
            <span className="mt-0.5 shrink-0">{config.icon}</span>
            <p className="flex-1 text-sm font-medium leading-snug">{t.message}</p>
            <button
              type="button"
              onClick={() => dismiss(t.id)}
              aria-label="Cerrar notificación"
              className="shrink-0 rounded-md p-0.5 text-muted-foreground transition-colors hover:text-foreground"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
