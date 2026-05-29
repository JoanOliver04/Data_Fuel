import { ArrowRight, MapPin, Sparkles } from "lucide-react";
import { memo } from "react";

import { cn } from "@/lib/utils";

import { deriveAlertView, PRIORITY_META } from "./priority";
import { alertMeta, TONE_CLASSES } from "./registry";
import type { AlertNotification } from "./types";

// ── Smart Fuel Alerts — notification (opportunity) card ───────────────────────
// Premium, mobile-first card for one delivered alert. It composes the registry
// (type → icon/label/tone), the priority engine (level + recommendation +
// savings) and the backend's already-validated copy (title/message). Every
// number shown is one the backend computed — the card never derives its own.

function relativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  const diffMin = Math.round((Date.now() - then) / 60_000);
  if (diffMin < 1) return "ahora";
  if (diffMin < 60) return `hace ${diffMin} min`;
  const h = Math.round(diffMin / 60);
  if (h < 24) return `hace ${h} h`;
  const days = Math.round(h / 24);
  return days === 1 ? "ayer" : `hace ${days} días`;
}

export const NotificationCard = memo(function NotificationCard({
  notification,
  unseen,
}: {
  notification: AlertNotification;
  /** Adds a subtle "new" accent for notifications past the last-seen marker. */
  unseen: boolean;
}) {
  const meta = alertMeta(notification.alert_type);
  const tone = TONE_CLASSES[meta.tone];
  const view = deriveAlertView(notification);
  const priority = PRIORITY_META[view.priority];
  const Icon = meta.icon;

  return (
    <article
      className={cn(
        "relative overflow-hidden rounded-2xl border border-border bg-card p-3.5 shadow-elevation-sm ring-1",
        view.priority === "high" ? tone.ring : "ring-transparent",
      )}
    >
      {/* Priority accent bar */}
      <span aria-hidden className={cn("absolute inset-y-0 left-0 w-1", priority.dot)} />

      <div className="pl-1.5">
        {/* Header: type + priority + time */}
        <div className="mb-1.5 flex items-center gap-2">
          <span className={cn("flex h-7 w-7 shrink-0 items-center justify-center rounded-lg", tone.chip)}>
            <Icon className={cn("h-4 w-4", tone.icon)} aria-hidden />
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-[13px] font-bold leading-tight text-foreground">
              {notification.title}
            </p>
            <p className="text-[11px] text-muted-foreground">{meta.short}</p>
          </div>
          {unseen && (
            <span
              className="mt-0.5 h-2 w-2 shrink-0 rounded-full bg-primary"
              aria-label="Nueva"
            />
          )}
        </div>

        {/* Priority + savings chips */}
        <div className="mb-2 flex flex-wrap items-center gap-1.5">
          <span
            className={cn(
              "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide",
              priority.chip,
            )}
          >
            {priority.label}
          </span>
          {view.savingsLabel !== null && (
            <span className={cn("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold tabular-nums", tone.chip)}>
              {view.savingsLabel}
            </span>
          )}
          {notification.source === "llm" && (
            <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-semibold text-primary">
              <Sparkles className="h-3 w-3" aria-hidden />
              IA
            </span>
          )}
        </div>

        {/* Recommendation (the action) */}
        {view.recommendation !== null && (
          <p className={cn("mb-1.5 flex items-center gap-1.5 text-sm font-semibold", tone.icon)}>
            <ArrowRight className="h-4 w-4 shrink-0" aria-hidden />
            {view.recommendation}
          </p>
        )}

        {/* Explanation — trustworthy backend copy */}
        <p className="text-[13px] leading-snug text-foreground/80">{notification.message}</p>

        {/* Footer: station + time */}
        <div className="mt-2 flex items-center justify-between text-[11px] text-muted-foreground">
          {view.stationLabel !== null ? (
            <span className="inline-flex min-w-0 items-center gap-1">
              <MapPin className="h-3 w-3 shrink-0" aria-hidden />
              <span className="truncate">{view.stationLabel}</span>
            </span>
          ) : (
            <span />
          )}
          <span className="shrink-0 tabular-nums">{relativeTime(notification.created_at)}</span>
        </div>
      </div>
    </article>
  );
});
