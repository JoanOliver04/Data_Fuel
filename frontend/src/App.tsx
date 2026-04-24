import { useEffect } from "react";

import { Providers } from "@/app/providers";
import { AppRoutes } from "@/app/router";
import { useSettingsStore } from "@/stores/settings.store";

function ThemeSync() {
  const theme = useSettingsStore((s) => s.theme);
  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
  }, [theme]);
  return null;
}

export function App() {
  return (
    <Providers>
      <ThemeSync />
      <AppRoutes />
    </Providers>
  );
}
