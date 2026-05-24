import { act, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { UserSelectedMarker } from "./UserSelectedMarker";

// Captured Leaflet wiring so we can drive drag events without a real map.
const mocks = vi.hoisted(() => ({
  latLng: { lat: 40.123456, lng: -3.654321 },
  handlers: null as null | { drag?: () => void; dragend?: () => void },
  draggable: undefined as boolean | undefined,
}));

vi.mock("react-leaflet", async () => {
  const React = await vi.importActual<typeof import("react")>("react");
  return {
    Marker: React.forwardRef(function Marker(
      props: {
        children?: React.ReactNode;
        draggable?: boolean;
        eventHandlers?: { drag?: () => void; dragend?: () => void };
      },
      ref: React.Ref<{ getLatLng: () => { lat: number; lng: number } }>,
    ) {
      React.useImperativeHandle(ref, () => ({ getLatLng: () => mocks.latLng }), []);
      mocks.handlers = props.eventHandlers ?? null;
      mocks.draggable = props.draggable;
      return React.createElement("div", { "data-testid": "user-pin" }, props.children);
    }),
    Popup: (props: { children?: React.ReactNode }) =>
      React.createElement("div", null, props.children),
  };
});

vi.mock("leaflet", () => ({ divIcon: vi.fn().mockReturnValue({}) }));

function renderMarker(overrides: Partial<Parameters<typeof UserSelectedMarker>[0]> = {}) {
  const props = {
    position: { lat: 40, lon: -3 },
    draggable: true,
    onDrag: vi.fn(),
    onDragEnd: vi.fn(),
    ...overrides,
  };
  render(<UserSelectedMarker {...props} />);
  return props;
}

describe("UserSelectedMarker", () => {
  it("renders exactly one pin marker", () => {
    renderMarker();
    expect(screen.getAllByTestId("user-pin")).toHaveLength(1);
  });

  it("is draggable only when pin mode is active", () => {
    renderMarker({ draggable: false });
    expect(mocks.draggable).toBe(false);
  });

  it("reports live coordinates while dragging", () => {
    const { onDrag } = renderMarker();
    act(() => mocks.handlers?.drag?.());
    expect(onDrag).toHaveBeenCalledWith(40.123456, -3.654321);
  });

  it("commits the final coordinate on drag end", () => {
    const { onDragEnd } = renderMarker();
    act(() => mocks.handlers?.dragend?.());
    expect(onDragEnd).toHaveBeenCalledWith(40.123456, -3.654321);
  });
});
