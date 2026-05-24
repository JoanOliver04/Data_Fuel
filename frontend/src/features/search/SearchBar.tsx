import { Loader2, MapPin, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";
import { useSettingsStore } from "@/stores/settings.store";
import { useSearchStore } from "@/stores/search.store";

interface NominatimResult {
  place_id: number;
  display_name: string;
  lat: string;
  lon: string;
  address?: {
    city?: string;
    town?: string;
    village?: string;
    municipality?: string;
  };
}

async function reverseGeocode(lat: number, lon: number): Promise<string> {
  try {
    const res = await fetch(
      `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json&zoom=10`,
      { headers: { "Accept-Language": "es", "User-Agent": "DataFuel/1.0" } },
    );
    if (!res.ok) return `${lat.toFixed(4)}, ${lon.toFixed(4)}`;
    const data = await res.json();
    const addr = data.address;
    return (
      addr?.city ?? addr?.town ?? addr?.village ?? addr?.municipality ?? `${lat.toFixed(4)}, ${lon.toFixed(4)}`
    );
  } catch {
    return `${lat.toFixed(4)}, ${lon.toFixed(4)}`;
  }
}

async function searchPlaces(query: string): Promise<NominatimResult[]> {
  try {
    const res = await fetch(
      `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(query)}&countrycodes=es&format=json&limit=5&addressdetails=1`,
      { headers: { "Accept-Language": "es", "User-Agent": "DataFuel/1.0" } },
    );
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

interface SearchBarProps {
  isSearching: boolean;
}

export function SearchBar({ isSearching }: SearchBarProps) {
  const { userLat, userLon, setLocation } = useSettingsStore();
  const { locationLabel, setLocationLabel, clearPin } = useSearchStore();

  const [inputValue, setInputValue] = useState(locationLabel);
  const [suggestions, setSuggestions] = useState<NominatimResult[]>([]);
  const [geoLoading, setGeoLoading] = useState(false);
  const [highlightedIdx, setHighlightedIdx] = useState(-1);
  const [showDropdown, setShowDropdown] = useState(false);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setInputValue(locationLabel);
  }, [locationLabel]);

  useEffect(() => {
    if (userLat !== null && userLon !== null && !locationLabel) {
      reverseGeocode(userLat, userLon).then(setLocationLabel);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    function onOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    }
    document.addEventListener("mousedown", onOutside);
    return () => document.removeEventListener("mousedown", onOutside);
  }, []);

  function handleInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    const val = e.target.value;
    setInputValue(val);
    setHighlightedIdx(-1);

    if (debounceRef.current) clearTimeout(debounceRef.current);

    if (!val.trim()) {
      setSuggestions([]);
      setShowDropdown(false);
      return;
    }

    debounceRef.current = setTimeout(async () => {
      const results = await searchPlaces(val);
      setSuggestions(results);
      setShowDropdown(results.length > 0);
    }, 300);
  }

  function handleSelect(result: NominatimResult) {
    const addr = result.address;
    const fallback = result.display_name.split(",")[0] ?? result.display_name;
    const label = addr?.city ?? addr?.town ?? addr?.village ?? addr?.municipality ?? fallback.trim();
    setLocationLabel(label);
    setInputValue(label);
    // A municipality/CP search explicitly overrides any manual pin.
    clearPin();
    setLocation(parseFloat(result.lat), parseFloat(result.lon));
    setSuggestions([]);
    setShowDropdown(false);
    inputRef.current?.blur();
  }

  function handleClear() {
    setInputValue("");
    setLocationLabel("");
    setSuggestions([]);
    setShowDropdown(false);
    inputRef.current?.focus();
  }

  async function handleDetect() {
    if (!navigator.geolocation) return;
    setGeoLoading(true);
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const lat = Math.round(pos.coords.latitude * 1e6) / 1e6;
        const lon = Math.round(pos.coords.longitude * 1e6) / 1e6;
        // Switching back to GPS exits pin mode and drops the manual pin.
        clearPin();
        setLocation(lat, lon);
        const label = await reverseGeocode(lat, lon);
        setLocationLabel(label);
        setInputValue(label);
        setGeoLoading(false);
      },
      () => setGeoLoading(false),
    );
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (!showDropdown || suggestions.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlightedIdx((i) => Math.min(i + 1, suggestions.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlightedIdx((i) => Math.max(i - 1, -1));
    } else if (e.key === "Enter" && highlightedIdx >= 0) {
      e.preventDefault();
      const target = suggestions[highlightedIdx];
      if (target) handleSelect(target);
    } else if (e.key === "Escape") {
      setShowDropdown(false);
      setHighlightedIdx(-1);
    }
  }

  const busy = geoLoading || isSearching;
  const hasValue = inputValue.length > 0;

  return (
    <div ref={containerRef} className="relative w-full">
      <div
        className={cn(
          "flex items-center gap-2 rounded-xl border bg-card px-3 py-2.5",
          "shadow-sm transition-all duration-200",
          "focus-within:border-primary/50 focus-within:shadow-[0_0_0_3px_hsl(var(--ring)/0.12),0_1px_3px_0_rgb(0_0_0/0.08)]",
        )}
      >
        {/* GPS button */}
        <button
          type="button"
          onClick={handleDetect}
          disabled={geoLoading}
          aria-label="Detectar mi ubicación"
          className={cn(
            "shrink-0 transition-colors duration-150",
            geoLoading ? "text-primary" : "text-muted-foreground hover:text-primary",
          )}
        >
          {geoLoading ? (
            <Loader2 className="h-5 w-5 animate-spin" />
          ) : (
            <MapPin className="h-5 w-5" />
          )}
        </button>

        {/* Text input */}
        <input
          ref={inputRef}
          type="text"
          value={inputValue}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onFocus={() => suggestions.length > 0 && setShowDropdown(true)}
          placeholder="¿Dónde quieres repostar?"
          aria-label="Ubicación de búsqueda"
          aria-autocomplete="list"
          aria-expanded={showDropdown}
          aria-activedescendant={highlightedIdx >= 0 ? `suggestion-${highlightedIdx}` : undefined}
          role="combobox"
          className="min-w-0 flex-1 bg-transparent text-sm font-medium outline-none placeholder:font-normal placeholder:text-muted-foreground"
        />

        {/* Right indicator */}
        {busy && !geoLoading ? (
          <Loader2 className="h-4 w-4 shrink-0 animate-spin text-muted-foreground" />
        ) : hasValue && !geoLoading ? (
          <button
            type="button"
            onClick={handleClear}
            aria-label="Limpiar búsqueda"
            className="shrink-0 rounded-full p-0.5 text-muted-foreground transition-colors hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        ) : null}
      </div>

      {/* Autocomplete dropdown */}
      {showDropdown && suggestions.length > 0 && (
        <ul
          role="listbox"
          aria-label="Sugerencias de ubicación"
          className="absolute left-0 right-0 top-full z-50 mt-1.5 overflow-hidden rounded-xl border border-border bg-card shadow-lg shadow-black/5 dark:shadow-black/30"
        >
          {suggestions.map((s, i) => {
            const parts = s.display_name.split(",");
            const primary = (parts[0] ?? s.display_name).trim();
            const secondary = parts.slice(1, 3).join(",").trim();
            return (
              <li
                key={s.place_id}
                id={`suggestion-${i}`}
                role="option"
                aria-selected={i === highlightedIdx}
                onMouseDown={(e) => {
                  e.preventDefault();
                  handleSelect(s);
                }}
                onMouseEnter={() => setHighlightedIdx(i)}
                className={cn(
                  "flex cursor-pointer items-start gap-3 px-4 py-2.5 text-sm transition-colors",
                  i === highlightedIdx ? "bg-accent" : "hover:bg-accent/60",
                )}
              >
                <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                <div className="min-w-0">
                  <div className="truncate font-medium">{primary}</div>
                  {secondary && (
                    <div className="truncate text-xs text-muted-foreground">{secondary}</div>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
