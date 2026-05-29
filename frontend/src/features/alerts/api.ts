import { apiFetch } from "@/lib/api-client";

import type { Alert, AlertCreate, AlertNotification, AlertUpdate } from "./types";

// ── Smart Fuel Alerts — API layer ────────────────────────────────────────────
// Thin typed wrappers over the backend alert/notification endpoints. No business
// logic lives here: evaluation, prediction reuse and copy generation all happen
// server-side. The frontend only manages alert configuration and reads the feed.

export function fetchAlerts(userIdentifier: string): Promise<Alert[]> {
  const qs = new URLSearchParams({ user_identifier: userIdentifier });
  return apiFetch<Alert[]>(`/api/v1/alerts?${qs}`);
}

export function createAlert(body: AlertCreate): Promise<Alert> {
  return apiFetch<Alert>("/api/v1/alerts", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function updateAlert(
  alertId: number,
  userIdentifier: string,
  body: AlertUpdate,
): Promise<Alert> {
  const qs = new URLSearchParams({ user_identifier: userIdentifier });
  return apiFetch<Alert>(`/api/v1/alerts/${alertId}?${qs}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function deleteAlert(alertId: number, userIdentifier: string): Promise<void> {
  const qs = new URLSearchParams({ user_identifier: userIdentifier });
  return apiFetch<void>(`/api/v1/alerts/${alertId}?${qs}`, { method: "DELETE" });
}

export function fetchNotifications(
  userIdentifier: string,
  limit = 50,
): Promise<AlertNotification[]> {
  const qs = new URLSearchParams({ user_identifier: userIdentifier, limit: String(limit) });
  return apiFetch<AlertNotification[]>(`/api/v1/notifications?${qs}`);
}
