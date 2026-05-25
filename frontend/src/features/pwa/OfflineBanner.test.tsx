import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { OfflineBanner } from "./OfflineBanner";

function setOnline(value: boolean): void {
  Object.defineProperty(navigator, "onLine", { configurable: true, value });
}

describe("OfflineBanner", () => {
  afterEach(() => setOnline(true));

  it("renders nothing while online", () => {
    setOnline(true);
    const { container } = render(<OfflineBanner />);
    expect(container).toBeEmptyDOMElement();
  });

  it("shows an offline status message when offline", () => {
    setOnline(false);
    render(<OfflineBanner />);
    const banner = screen.getByRole("status");
    expect(banner).toHaveTextContent(/sin conexión/i);
  });
});
