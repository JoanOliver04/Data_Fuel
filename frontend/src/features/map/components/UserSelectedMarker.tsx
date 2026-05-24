import { divIcon, type DivIcon, type Marker as LeafletMarker } from "leaflet";
import { useMemo, useRef } from "react";
import { Marker, Popup } from "react-leaflet";

import type { PinLocation } from "@/stores/search.store";

// User-location-themed pin: a violet teardrop with a white core and a soft
// pulse halo — deliberately distinct from the ranked amber station markers and
// the blue "current GPS position" dot. The animations live on the inner
// wrapper (`.df-pin`), never on the element Leaflet positions, so the entrance
// transform can't fight Leaflet's translate. `prefers-reduced-motion` is
// honoured globally in index.css.
function makePinIcon(): DivIcon {
  return divIcon({
    className: "",
    html: `
      <div class="df-pin" role="img" aria-label="Ubicación seleccionada">
        <span class="df-pin__pulse"></span>
        <svg width="30" height="40" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="position:relative;display:block">
          <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z" fill="#7c3aed" stroke="#ffffff" stroke-width="1.75" stroke-linejoin="round"/>
          <circle cx="12" cy="10" r="3.2" fill="#ffffff"/>
        </svg>
      </div>`,
    iconSize: [30, 40],
    iconAnchor: [15, 38],
    popupAnchor: [0, -36],
  });
}

// Built once — the icon has no per-instance state, so re-creating it on every
// render would only churn the DOM and re-trigger the drop animation.
const PIN_ICON = makePinIcon();

interface UserSelectedMarkerProps {
  position: PinLocation;
  /** When true the marker can be dragged (pin mode is active). */
  draggable: boolean;
  /** Live drag feedback — fired continuously while dragging. */
  onDrag: (lat: number, lon: number) => void;
  /** Drag released — fired with the final coordinate. */
  onDragEnd: (lat: number, lon: number) => void;
}

export function UserSelectedMarker({
  position,
  draggable,
  onDrag,
  onDragEnd,
}: UserSelectedMarkerProps) {
  const markerRef = useRef<LeafletMarker | null>(null);

  // Read the live coordinate straight off the Leaflet marker (canonical
  // react-leaflet draggable pattern) rather than controlling `position` during
  // the drag, which would snap the marker and feel janky.
  const eventHandlers = useMemo(
    () => ({
      drag() {
        const ll = markerRef.current?.getLatLng();
        if (ll) onDrag(ll.lat, ll.lng);
      },
      dragend() {
        const ll = markerRef.current?.getLatLng();
        if (ll) onDragEnd(ll.lat, ll.lng);
      },
    }),
    [onDrag, onDragEnd],
  );

  return (
    <Marker
      ref={markerRef}
      position={[position.lat, position.lon]}
      icon={PIN_ICON}
      draggable={draggable}
      eventHandlers={eventHandlers}
      zIndexOffset={1500}
      keyboard={false}
    >
      <Popup>📍 Tu ubicación seleccionada</Popup>
    </Marker>
  );
}
