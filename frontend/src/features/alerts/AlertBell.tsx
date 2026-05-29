import { Bell } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useSettingsStore } from "@/stores/settings.store";

import { useNotifications } from "./hooks";
import { useAlertUiStore } from "./store";

// ── Smart Fuel Alerts — header bell ──────────────────────────────────────────
// The always-visible entry point. Polls the notification feed in the background
// so the unread badge surfaces opportunities even before the user opens the
// center — the core "proactive, not passive" behaviour. Shares the query key
// with the center, so there is exactly one feed request.

export function AlertBell() {
  const open = useAlertUiStore((s) => s.open);
  const lastSeenId = useAlertUiStore((s) => s.lastSeenId);
  const userId = useSettingsStore((s) => s.alertsUserId);
  const { data } = useNotifications(userId);

  const unread = (data ?? []).filter((n) => n.id > lastSeenId).length;

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={open}
      aria-label={unread > 0 ? `Alertas (${unread} sin leer)` : "Alertas"}
      className="relative h-9 w-9 rounded-lg text-muted-foreground hover:text-foreground"
    >
      <Bell className="h-4 w-4" />
      {unread > 0 && (
        <span className="absolute right-1 top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[9px] font-bold leading-none text-white tabular-nums">
          {unread > 9 ? "9+" : unread}
        </span>
      )}
    </Button>
  );
}
