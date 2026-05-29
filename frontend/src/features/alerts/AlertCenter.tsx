import { BellRing, Inbox, Plus, SlidersHorizontal } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import { useSettingsStore } from "@/stores/settings.store";

import { AlertForm } from "./AlertForm";
import { AlertRow } from "./AlertRow";
import { NotificationCard } from "./NotificationCard";
import { useAlerts, useNotifications } from "./hooks";
import { sortByPriority } from "./priority";
import { useAlertUiStore } from "./store";

// ── Smart Fuel Alerts — Alert Center ─────────────────────────────────────────
// The dedicated hub. Two tabs: "Oportunidades" (the prioritised notification
// feed — triggered alerts and AI-detected opportunities) and "Mis alertas"
// (manage active alerts + create). Opening the feed marks everything seen, which
// clears the unread badge on the bell.

type Tab = "feed" | "manage";

function TabButton({
  active,
  onClick,
  icon: Icon,
  label,
  badge,
}: {
  active: boolean;
  onClick: () => void;
  icon: typeof Inbox;
  label: string;
  badge?: number;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "relative flex flex-1 items-center justify-center gap-1.5 border-b-2 py-2.5 text-sm font-medium transition-colors",
        active
          ? "border-primary text-foreground"
          : "border-transparent text-muted-foreground hover:text-foreground",
      )}
    >
      <Icon className="h-4 w-4" aria-hidden />
      {label}
      {badge !== undefined && badge > 0 && (
        <span className="ml-0.5 inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-1 text-[10px] font-bold text-primary-foreground tabular-nums">
          {badge}
        </span>
      )}
    </button>
  );
}

function EmptyState({ icon: Icon, title, hint }: { icon: typeof Inbox; title: string; hint: string }) {
  return (
    <div className="flex flex-col items-center gap-2 px-6 py-12 text-center">
      <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-muted">
        <Icon className="h-6 w-6 text-muted-foreground" aria-hidden />
      </span>
      <p className="text-sm font-semibold text-foreground">{title}</p>
      <p className="max-w-[16rem] text-xs text-muted-foreground">{hint}</p>
    </div>
  );
}

export function AlertCenter() {
  const isOpen = useAlertUiStore((s) => s.isOpen);
  const close = useAlertUiStore((s) => s.close);
  const lastSeenId = useAlertUiStore((s) => s.lastSeenId);
  const markSeen = useAlertUiStore((s) => s.markSeen);
  const userId = useSettingsStore((s) => s.alertsUserId);

  const [tab, setTab] = useState<Tab>("feed");
  const [showForm, setShowForm] = useState(false);

  const { data: notifications, isLoading: feedLoading } = useNotifications(userId, isOpen);
  const { data: alerts, isLoading: alertsLoading } = useAlerts(isOpen ? userId : null);

  const sorted = useMemo(() => sortByPriority(notifications ?? []), [notifications]);
  const unseenCount = useMemo(
    () => (notifications ?? []).filter((n) => n.id > lastSeenId).length,
    [notifications, lastSeenId],
  );

  // Viewing the feed clears the unread marker.
  useEffect(() => {
    if (isOpen && tab === "feed" && sorted.length > 0) {
      markSeen(Math.max(...sorted.map((n) => n.id)));
    }
  }, [isOpen, tab, sorted, markSeen]);

  return (
    <Dialog open={isOpen} onOpenChange={(o) => (o ? undefined : close())}>
      <DialogContent className="flex max-h-[88vh] w-[calc(100vw-1.5rem)] max-w-md flex-col overflow-hidden p-0">
        <div className="flex items-center gap-2 border-b border-border px-4 py-3.5">
          <BellRing className="h-4 w-4 shrink-0 text-primary" aria-hidden />
          <DialogTitle className="text-base">Alertas inteligentes</DialogTitle>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-border px-2">
          <TabButton
            active={tab === "feed"}
            onClick={() => setTab("feed")}
            icon={Inbox}
            label="Oportunidades"
            badge={unseenCount}
          />
          <TabButton
            active={tab === "manage"}
            onClick={() => setTab("manage")}
            icon={SlidersHorizontal}
            label="Mis alertas"
          />
        </div>

        <div className="flex-1 overflow-y-auto overscroll-contain p-4">
          {tab === "feed" ? (
            feedLoading ? (
              <FeedSkeleton />
            ) : sorted.length === 0 ? (
              <EmptyState
                icon={Inbox}
                title="Sin oportunidades por ahora"
                hint="Cuando una alerta se cumpla o detectemos una buena ocasión, aparecerá aquí."
              />
            ) : (
              <div className="space-y-2.5">
                {sorted.map((n) => (
                  <NotificationCard key={n.id} notification={n} unseen={n.id > lastSeenId} />
                ))}
              </div>
            )
          ) : showForm ? (
            <AlertForm userId={userId} onCreated={() => setShowForm(false)} />
          ) : (
            <div className="space-y-3">
              <button
                type="button"
                onClick={() => setShowForm(true)}
                className="flex w-full items-center justify-center gap-2 rounded-xl border border-dashed border-primary/40 bg-primary/5 py-2.5 text-sm font-semibold text-primary transition-colors hover:bg-primary/10"
              >
                <Plus className="h-4 w-4" />
                Nueva alerta
              </button>

              {alertsLoading ? (
                <FeedSkeleton />
              ) : (alerts ?? []).length === 0 ? (
                <EmptyState
                  icon={SlidersHorizontal}
                  title="Aún no tienes alertas"
                  hint="Crea una alerta de precio o deja que la IA vigile las oportunidades por ti."
                />
              ) : (
                <div className="space-y-1.5">
                  {(alerts ?? []).map((a) => (
                    <AlertRow key={a.id} alert={a} userId={userId} />
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

function FeedSkeleton() {
  return (
    <div className="space-y-2.5">
      {[0, 1, 2].map((i) => (
        <div key={i} className="animate-pulse rounded-2xl border border-border bg-card p-3.5">
          <div className="mb-2 h-3.5 w-2/3 rounded-full bg-muted" />
          <div className="mb-1.5 h-3 w-1/3 rounded-full bg-muted" />
          <div className="h-3 w-full rounded-full bg-muted" />
        </div>
      ))}
    </div>
  );
}
