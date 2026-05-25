import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useNotificationPermission } from "./useNotificationPermission";

interface NotificationStub {
  permission: NotificationPermission;
  requestPermission: () => Promise<NotificationPermission>;
}

const holder = globalThis as { Notification?: unknown };
const original = holder.Notification;

afterEach(() => {
  if (original === undefined) Reflect.deleteProperty(holder, "Notification");
  else holder.Notification = original;
});

describe("useNotificationPermission", () => {
  it("reports unsupported when the Notification API is absent", () => {
    Reflect.deleteProperty(holder, "Notification");
    const { result } = renderHook(() => useNotificationPermission());
    expect(result.current.permission).toBe("unsupported");
    expect(result.current.supported).toBe(false);
  });

  it("requests and reflects a granted permission", async () => {
    const stub: NotificationStub = {
      permission: "default",
      requestPermission: vi.fn().mockResolvedValue("granted"),
    };
    holder.Notification = stub;

    const { result } = renderHook(() => useNotificationPermission());
    expect(result.current.permission).toBe("default");

    await act(async () => {
      await result.current.request();
    });
    expect(result.current.permission).toBe("granted");
    expect(stub.requestPermission).toHaveBeenCalledOnce();
  });
});
