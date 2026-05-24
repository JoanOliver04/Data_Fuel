import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { PinLocationControl } from "./PinLocationControl";

describe("PinLocationControl", () => {
  it("renders an accessible toggle button", () => {
    render(<PinLocationControl active={false} onToggle={() => {}} />);
    const btn = screen.getByRole("button", { name: "Seleccionar ubicación exacta" });
    expect(btn).toHaveAttribute("aria-pressed", "false");
  });

  it("reflects the active state via aria-pressed", () => {
    render(<PinLocationControl active onToggle={() => {}} />);
    expect(
      screen.getByRole("button", { name: /seleccionar ubicación exacta/i }),
    ).toHaveAttribute("aria-pressed", "true");
  });

  it("calls onToggle when clicked", async () => {
    const onToggle = vi.fn();
    const user = userEvent.setup();
    render(<PinLocationControl active={false} onToggle={onToggle} />);

    await user.click(screen.getByRole("button", { name: /seleccionar ubicación exacta/i }));
    expect(onToggle).toHaveBeenCalledTimes(1);
  });
});
