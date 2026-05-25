/**
 * Structured PWA telemetry.
 *
 * Thin wrapper over the app logger so install / offline / service-worker
 * lifecycle events are observable in the console (and easy to forward to a
 * real analytics sink later). Never throws — observability must not break the
 * app.
 */

import { createLogger } from "@/lib/logger";

const log = createLogger("pwa");

export type PWAEvent =
  | "install_prompt_shown"
  | "install_accepted"
  | "install_dismissed"
  | "offline_entered"
  | "offline_exited"
  | "sw_registered"
  | "sw_offline_ready"
  | "sw_updated"
  | "sw_register_failed"
  | "sw_cache_error"
  | "notification_permission";

export function trackPWA(event: PWAEvent, detail: Record<string, unknown> = {}): void {
  try {
    if (event === "sw_register_failed" || event === "sw_cache_error") {
      log.error(`pwa:${event}`, detail);
    } else {
      log.info(`pwa:${event}`, detail);
    }
  } catch {
    /* logging must never break the app */
  }
}
