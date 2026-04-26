import { Loader2 } from "lucide-react";
import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";

import { Home } from "@/pages/Home";

// Secondary routes load on navigation, keeping the initial bundle smaller.
const Settings = lazy(() =>
  import("@/pages/Settings").then((m) => ({ default: m.Settings })),
);
const NotFound = lazy(() =>
  import("@/pages/NotFound").then((m) => ({ default: m.NotFound })),
);

function RouteFallback() {
  return (
    <div className="flex h-dvh items-center justify-center bg-background">
      <Loader2 className="h-6 w-6 animate-spin text-primary" />
    </div>
  );
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route
        path="/settings"
        element={
          <Suspense fallback={<RouteFallback />}>
            <Settings />
          </Suspense>
        }
      />
      <Route
        path="*"
        element={
          <Suspense fallback={<RouteFallback />}>
            <NotFound />
          </Suspense>
        }
      />
    </Routes>
  );
}
