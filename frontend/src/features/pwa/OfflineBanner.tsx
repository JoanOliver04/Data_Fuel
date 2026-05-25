import { WifiOff } from "lucide-react";
import { useEffect, useRef } from "react";

import { cn } from "@/lib/utils";
import { trackPWA } from "@/features/pwa/telemetry";
import { useOnlineStatus } from "@/features/pwa/useOnlineStatus";

interface OfflineBannerProps {
  className?: string;
}

/**
 * Global, top-anchored "you are offline" banner. The app shell stays usable
 * offline (cached) and cached API reads still render; this just sets honest
 * expectations. Safe-area aware so it clears the notch on installed iOS.
 */
export function OfflineBanner({ className }: OfflineBannerProps) {
  const online = useOnlineStatus();
  const wasOffline = useRef(false);

  useEffect(() => {
    if (!online) {
      trackPWA("offline_entered");
      wasOffline.current = true;
    } else if (wasOffline.current) {
      trackPWA("offline_exited");
      wasOffline.current = false;
    }
  }, [online]);

  if (online) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        "fixed inset-x-0 top-0 z-[60] flex items-center justify-center gap-2",
        "bg-amber-500/95 px-4 pb-2 text-amber-950 shadow-md backdrop-blur",
        "pt-[max(0.5rem,env(safe-area-inset-top))] text-xs font-medium",
        "motion-safe:animate-in motion-safe:slide-in-from-top-2 motion-safe:duration-300",
        className,
      )}
    >
      <WifiOff className="h-4 w-4 shrink-0" aria-hidden="true" />
      <span>Sin conexión — mostrando los últimos datos en caché.</span>
    </div>
  );
}
