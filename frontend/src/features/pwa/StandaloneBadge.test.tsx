import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { StandaloneBadge } from "./StandaloneBadge";

const originalMatchMedia = window.matchMedia;

afterEach(() => {
  window.matchMedia = originalMatchMedia;
});

function mockStandalone(matches: boolean) {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: query === "(display-mode: standalone)" ? matches : false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })) as unknown as typeof window.matchMedia;
}

describe("StandaloneBadge", () => {
  it("renders nothing in browser tab mode", () => {
    mockStandalone(false);
    const { container } = render(<StandaloneBadge />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders App badge when running standalone", () => {
    mockStandalone(true);
    render(<StandaloneBadge />);
    expect(screen.getByText(/^app$/i)).toBeInTheDocument();
  });
});
