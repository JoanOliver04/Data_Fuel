import { useEffect, useRef } from "react";

import { Providers } from "@/app/providers";
import { AppRoutes } from "@/app/router";
import { Toaster } from "@/components/ui/toaster";
import { OfflineBanner } from "@/features/pwa/OfflineBanner";
import { useSettingsStore } from "@/stores/settings.store";

function ThemeSync() {
  const theme = useSettingsStore((s) => s.theme);
  const firstRun = useRef(true);

  useEffect(() => {
    const root = document.documentElement;
    // Glide colours on theme switch only — never on first paint (avoids a flash)
    // and never during hovers/scroll (the class is removed right after).
    if (!firstRun.current) {
      root.classList.add("theme-transition");
      window.setTimeout(() => root.classList.remove("theme-transition"), 320);
    }
    firstRun.current = false;
    root.classList.toggle("dark", theme === "dark");
  }, [theme]);

  return null;
}

export function App() {
  return (
    <Providers>
      <ThemeSync />
      <OfflineBanner />
      <AppRoutes />
      <Toaster />
    </Providers>
  );
}
