import { useCallback, useState } from "react";

import { trackPWA } from "@/features/pwa/telemetry";

/**
 * Notification-permission flow — the push-notification-ready seam.
 *
 * This intentionally does NOT subscribe to push yet. It exposes the permission
 * state + a request action so the future alert/push integration only has to add
 * the `pushManager.subscribe()` call behind a `granted` permission. SSR-safe and
 * degrades to "unsupported" where the Notification API is absent (e.g. iOS web
 * outside standalone).
 */
export type PermissionState = NotificationPermission | "unsupported";

function readPermission(): PermissionState {
  if (typeof window === "undefined" || !("Notification" in window)) return "unsupported";
  return Notification.permission;
}

interface NotificationPermissionApi {
  permission: PermissionState;
  supported: boolean;
  request: () => Promise<PermissionState>;
}

export function useNotificationPermission(): NotificationPermissionApi {
  const [permission, setPermission] = useState<PermissionState>(readPermission);

  const request = useCallback(async (): Promise<PermissionState> => {
    if (typeof window === "undefined" || !("Notification" in window)) return "unsupported";
    const result = await Notification.requestPermission();
    setPermission(result);
    trackPWA("notification_permission", { result });
    return result;
  }, []);

  return { permission, supported: permission !== "unsupported", request };
}
