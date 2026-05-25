import { registerSW } from "virtual:pwa-register";

import { trackPWA } from "@/features/pwa/telemetry";

/**
 * Register the Workbox service worker and surface its lifecycle as telemetry.
 *
 * The manifest uses `registerType: "autoUpdate"`, so a new SW activates and
 * reloads automatically — we only observe here. Wrapped so a failed/blocked
 * registration (private mode, unsupported browser) NEVER breaks the app.
 */
export function registerPWA(): void {
  if (typeof window === "undefined" || !("serviceWorker" in navigator)) return;
  try {
    const updateSW = registerSW({
      immediate: true,
      onRegisteredSW: (swUrl) => trackPWA("sw_registered", { swUrl }),
      onRegisterError: (error) => trackPWA("sw_register_failed", { error: String(error) }),
      onOfflineReady: () => trackPWA("sw_offline_ready"),
      onNeedRefresh: () => {
        // autoUpdate normally reloads on its own; apply explicitly as a safety net.
        trackPWA("sw_updated");
        void updateSW(true);
      },
    });
  } catch (error) {
    trackPWA("sw_register_failed", { error: String(error) });
  }
}
