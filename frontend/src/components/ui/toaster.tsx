import { CheckCircle2, Info, X, XCircle } from "lucide-react";

import { useToastStore, type Toast } from "@/stores/toast.store";

const VARIANT_STYLES: Record<Toast["variant"], string> = {
  success: "border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
  error: "border-destructive/40 bg-destructive/10 text-destructive",
  info: "border-border bg-background text-foreground",
};

const VARIANT_ICONS: Record<Toast["variant"], React.ReactNode> = {
  success: <CheckCircle2 className="h-4 w-4" aria-hidden />,
  error: <XCircle className="h-4 w-4" aria-hidden />,
  info: <Info className="h-4 w-4" aria-hidden />,
};

export function Toaster() {
  const toasts = useToastStore((s) => s.toasts);
  const dismiss = useToastStore((s) => s.dismiss);

  return (
    <div
      role="region"
      aria-live="polite"
      aria-label="Notificaciones"
      className="pointer-events-none fixed inset-x-0 bottom-4 z-50 flex flex-col items-center gap-2 px-4"
    >
      {toasts.map((t) => (
        <div
          key={t.id}
          role="status"
          className={`pointer-events-auto flex w-full max-w-sm items-start gap-2 rounded-lg border px-3 py-2 text-sm shadow-md ${VARIANT_STYLES[t.variant]}`}
        >
          <span className="mt-0.5 shrink-0">{VARIANT_ICONS[t.variant]}</span>
          <p className="flex-1 leading-snug">{t.message}</p>
          <button
            type="button"
            onClick={() => dismiss(t.id)}
            aria-label="Cerrar notificación"
            className="shrink-0 rounded p-0.5 opacity-70 transition-opacity hover:opacity-100"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      ))}
    </div>
  );
}
