import { ArrowRight, Download, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useInstallPrompt } from "@/features/pwa/usePWA";
import { cn } from "@/lib/utils";

interface InstallPromptProps {
  className?: string;
}

export function InstallPrompt({ className }: InstallPromptProps) {
  const { canInstall, promptInstall, dismiss } = useInstallPrompt();

  if (!canInstall) return null;

  return (
    <div
      role="region"
      aria-label="Instalar Data Fuel"
      className={cn(
        "pointer-events-auto fixed inset-x-0 bottom-3 z-50 mx-auto flex max-w-md items-center gap-3",
        "rounded-2xl border border-border bg-background/95 px-4 py-3 shadow-2xl shadow-black/10 backdrop-blur-xl",
        "supports-[backdrop-filter]:bg-background/80 dark:shadow-black/40",
        className,
      )}
    >
      <div
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary"
        aria-hidden="true"
      >
        <Download className="h-5 w-5" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold leading-tight">Instala Data Fuel</p>
        <p className="text-xs text-muted-foreground">Acceso rápido y uso offline.</p>
      </div>
      <Button
        size="sm"
        onClick={() => {
          void promptInstall();
        }}
        className="h-8 gap-1 px-3 text-xs"
      >
        Instalar
        <ArrowRight className="h-3.5 w-3.5" />
      </Button>
      <Button
        variant="ghost"
        size="icon"
        onClick={dismiss}
        aria-label="Descartar invitación de instalación"
        className="h-8 w-8 shrink-0 rounded-lg text-muted-foreground hover:text-foreground"
      >
        <X className="h-4 w-4" />
      </Button>
    </div>
  );
}
