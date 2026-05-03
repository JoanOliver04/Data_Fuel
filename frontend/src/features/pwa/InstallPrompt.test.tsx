import { fireEvent, render, screen, act } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { InstallPrompt } from "./InstallPrompt";
import { INSTALL_DISMISSED_KEY, type BeforeInstallPromptEvent } from "./usePWA";

function fireInstallPromptEvent(): BeforeInstallPromptEvent {
  let userChoiceResolve: (v: { outcome: "accepted" | "dismissed"; platform: string }) => void =
    () => {};
  const userChoice = new Promise<{ outcome: "accepted" | "dismissed"; platform: string }>(
    (resolve) => {
      userChoiceResolve = resolve;
    },
  );

  const event = new Event("beforeinstallprompt") as unknown as BeforeInstallPromptEvent & {
    resolveChoice: (outcome: "accepted" | "dismissed") => void;
  };
  Object.defineProperties(event, {
    platforms: { value: ["web"] },
    userChoice: { value: userChoice },
    prompt: { value: () => Promise.resolve() },
    resolveChoice: {
      value: (outcome: "accepted" | "dismissed") =>
        userChoiceResolve({ outcome, platform: "web" }),
    },
  });

  act(() => {
    window.dispatchEvent(event);
  });
  return event;
}

describe("InstallPrompt", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });
  afterEach(() => {
    window.localStorage.clear();
  });

  it("renders nothing before beforeinstallprompt fires", () => {
    render(<InstallPrompt />);
    expect(screen.queryByRole("region", { name: /instalar/i })).not.toBeInTheDocument();
  });

  it("shows banner after beforeinstallprompt fires", () => {
    render(<InstallPrompt />);
    fireInstallPromptEvent();
    expect(screen.getByRole("region", { name: /instalar/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^instalar$/i })).toBeInTheDocument();
  });

  it("hides banner and persists dismissal in localStorage on dismiss", () => {
    render(<InstallPrompt />);
    fireInstallPromptEvent();
    fireEvent.click(screen.getByRole("button", { name: /descartar/i }));
    expect(screen.queryByRole("region", { name: /instalar/i })).not.toBeInTheDocument();
    expect(window.localStorage.getItem(INSTALL_DISMISSED_KEY)).toBe("1");
  });

  it("does not show banner if previously dismissed", () => {
    window.localStorage.setItem(INSTALL_DISMISSED_KEY, "1");
    render(<InstallPrompt />);
    fireInstallPromptEvent();
    expect(screen.queryByRole("region", { name: /instalar/i })).not.toBeInTheDocument();
  });
});
