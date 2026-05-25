import { useSyncExternalStore } from "react";

/**
 * Reactive online/offline status backed by the browser `online`/`offline`
 * events. SSR-safe (assumes online) and concurrent-safe via
 * `useSyncExternalStore`. Telemetry for transitions lives in the consumer
 * (OfflineBanner) so it fires once, not per subscriber.
 */

function subscribe(onChange: () => void): () => void {
  if (typeof window === "undefined") return () => {};
  window.addEventListener("online", onChange);
  window.addEventListener("offline", onChange);
  return () => {
    window.removeEventListener("online", onChange);
    window.removeEventListener("offline", onChange);
  };
}

function getSnapshot(): boolean {
  return typeof navigator === "undefined" ? true : navigator.onLine;
}

function getServerSnapshot(): boolean {
  return true;
}

export function useOnlineStatus(): boolean {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
