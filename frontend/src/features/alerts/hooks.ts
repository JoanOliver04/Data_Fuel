import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useToastStore } from "@/stores/toast.store";

import { createAlert, deleteAlert, fetchAlerts, fetchNotifications, updateAlert } from "./api";
import type { Alert, AlertCreate, AlertUpdate } from "./types";

// ── Smart Fuel Alerts — data hooks ───────────────────────────────────────────
// React Query wrappers. Queries are keyed by the per-device user identifier so a
// user only ever sees their own alerts/notifications. Mutations invalidate the
// alert list; the notification feed is owned by the scheduler, so it is only
// refetched on a poll interval, never written from the client.

const alertsKey = (userId: string) => ["alerts", userId] as const;
const notificationsKey = (userId: string) => ["notifications", userId] as const;

export function useAlerts(userId: string | null) {
  return useQuery({
    queryKey: alertsKey(userId ?? ""),
    queryFn: () => fetchAlerts(userId!),
    enabled: userId !== null,
    staleTime: 60_000,
  });
}

export function useNotifications(userId: string | null, enabled = true) {
  return useQuery({
    queryKey: notificationsKey(userId ?? ""),
    queryFn: () => fetchNotifications(userId!),
    enabled: userId !== null && enabled,
    staleTime: 60_000,
    // Background opportunities arrive on the scheduler's cadence; a gentle poll
    // surfaces them without the user reopening the center.
    refetchInterval: 5 * 60_000,
  });
}

export function useCreateAlert(userId: string) {
  const qc = useQueryClient();
  const show = useToastStore((s) => s.show);
  return useMutation({
    mutationFn: (body: AlertCreate) => createAlert(body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: alertsKey(userId) });
      show("Alerta creada", "success");
    },
    onError: () => show("No se pudo crear la alerta", "error"),
  });
}

export function useUpdateAlert(userId: string) {
  const qc = useQueryClient();
  const show = useToastStore((s) => s.show);
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: AlertUpdate }) =>
      updateAlert(id, userId, body),
    // Optimistic toggle keeps the enable/disable switch feeling instant. Only
    // `is_enabled` is patched locally (threshold_price is a string on the wire
    // but a number on input, so we let the refetch reconcile the rest).
    onMutate: async ({ id, body }) => {
      await qc.cancelQueries({ queryKey: alertsKey(userId) });
      const previous = qc.getQueryData<Alert[]>(alertsKey(userId));
      if (previous && body.is_enabled !== undefined) {
        const enabled = body.is_enabled;
        qc.setQueryData<Alert[]>(
          alertsKey(userId),
          previous.map((a) => (a.id === id ? { ...a, is_enabled: enabled } : a)),
        );
      }
      return { previous };
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) qc.setQueryData(alertsKey(userId), context.previous);
      show("No se pudo actualizar la alerta", "error");
    },
    onSettled: () => void qc.invalidateQueries({ queryKey: alertsKey(userId) }),
  });
}

export function useDeleteAlert(userId: string) {
  const qc = useQueryClient();
  const show = useToastStore((s) => s.show);
  return useMutation({
    mutationFn: (id: number) => deleteAlert(id, userId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: alertsKey(userId) });
      show("Alerta eliminada", "info");
    },
    onError: () => show("No se pudo eliminar la alerta", "error"),
  });
}
