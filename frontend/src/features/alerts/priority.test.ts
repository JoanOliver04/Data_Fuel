import { describe, expect, it } from "vitest";

import { deriveAlertView, sortByPriority } from "./priority";
import type { AlertNotification } from "./types";

// Minimal builder — only the fields the engine reads. Defaults make a neutral
// info notification; override per case.
function notif(overrides: Partial<AlertNotification>): AlertNotification {
  return {
    id: 1,
    alert_id: 1,
    user_identifier: "u",
    alert_type: "WEEKLY_SUMMARY",
    channel: "in_app",
    title: "t",
    message: "m",
    source: "deterministic",
    data: {},
    created_at: "2026-05-29T10:00:00Z",
    ...overrides,
  };
}

describe("deriveAlertView", () => {
  it("flags a hit price-objective alert as high priority with an act-now action", () => {
    const v = deriveAlertView(
      notif({
        alert_type: "PRICE_BELOW_THRESHOLD",
        data: { price: 1.4, target: 1.42, station: "Repsol (Alzira)" },
      }),
    );
    expect(v.priority).toBe("high");
    expect(v.recommendation).toMatch(/Reposta/i);
    expect(v.stationLabel).toBe("Repsol (Alzira)");
    expect(v.savingsLabel).not.toBeNull();
  });

  it("scales prediction trend priority by magnitude and picks direction-aware copy", () => {
    const big = deriveAlertView(
      notif({ alert_type: "PREDICTION_TREND", data: { change_pct: -3.1 } }),
    );
    expect(big.priority).toBe("high");
    expect(big.recommendation).toMatch(/esperar/i);

    const rising = deriveAlertView(
      notif({ alert_type: "PREDICTION_TREND", data: { change_pct: 1.0 } }),
    );
    expect(rising.priority).toBe("medium");
    expect(rising.recommendation).toMatch(/antes de la subida/i);
  });

  it("never fabricates figures when the payload omits them", () => {
    const v = deriveAlertView(notif({ alert_type: "TOTAL_COST_DROP", data: {} }));
    expect(v.savingsLabel).toBeNull();
  });

  it("treats a rising favourite-station change as informational, a drop as actionable", () => {
    expect(deriveAlertView(notif({ alert_type: "FAVORITE_STATION_CHANGE", data: { delta: 0.03 } })).priority).toBe("info");
    const drop = deriveAlertView(notif({ alert_type: "FAVORITE_STATION_CHANGE", data: { delta: -0.03 } }));
    expect(drop.priority).toBe("medium");
    expect(drop.recommendation).not.toBeNull();
  });

  it("degrades unknown future types to a safe informational card", () => {
    const v = deriveAlertView(notif({ alert_type: "TRAFFIC_WINDOW", data: {} }));
    expect(v.priority).toBe("info");
    expect(v.recommendation).toBeNull();
  });
});

describe("sortByPriority", () => {
  it("orders high → medium → info, then most recent first within a level", () => {
    const info = notif({ id: 1, alert_type: "WEEKLY_SUMMARY" });
    const highOld = notif({
      id: 2,
      alert_type: "PRICE_BELOW_THRESHOLD",
      data: { price: 1.4, target: 1.42 },
      created_at: "2026-05-29T08:00:00Z",
    });
    const highNew = notif({
      id: 3,
      alert_type: "PRICE_BELOW_THRESHOLD",
      data: { price: 1.4, target: 1.42 },
      created_at: "2026-05-29T09:00:00Z",
    });

    const sorted = sortByPriority([info, highOld, highNew]);
    expect(sorted.map((n) => n.id)).toEqual([3, 2, 1]);
  });

  it("does not mutate the input array", () => {
    const input = [notif({ id: 1 }), notif({ id: 2 })];
    const snapshot = [...input];
    sortByPriority(input);
    expect(input).toEqual(snapshot);
  });
});
