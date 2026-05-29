import { Calculator, List, Map, Settings } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";

import { cn } from "@/lib/utils";
import { useUiStore } from "@/stores/ui.store";

type NavTab = "map" | "list" | "simulator" | "settings";

const TABS = [
  { tab: "map" as NavTab, label: "Mapa", Icon: Map },
  { tab: "list" as NavTab, label: "Lista", Icon: List },
  { tab: "simulator" as NavTab, label: "Simular", Icon: Calculator },
  { tab: "settings" as NavTab, label: "Ajustes", Icon: Settings },
] as const;

export function BottomNav() {
  const location = useLocation();
  const navigate = useNavigate();
  const snap = useUiStore((s) => s.snap);
  const setSnap = useUiStore((s) => s.setSnap);

  function getActiveTab(): NavTab {
    if (location.pathname === "/simulator") return "simulator";
    if (location.pathname === "/settings") return "settings";
    return snap === "peek" ? "map" : "list";
  }

  const activeTab = getActiveTab();

  function handlePress(tab: NavTab) {
    navigator.vibrate?.(10);
    if (tab === "map") { navigate("/"); setSnap("peek"); }
    else if (tab === "list") { navigate("/"); setSnap("half"); }
    else if (tab === "simulator") navigate("/simulator");
    else navigate("/settings");
  }

  return (
    <nav
      aria-label="Navegación principal"
      className={cn(
        "fixed inset-x-0 bottom-0 z-50 lg:hidden",
        "rounded-t-[20px] border-t border-border",
        "bg-background/90 backdrop-blur-xl supports-[backdrop-filter]:bg-background/85",
        "shadow-[0_-6px_24px_rgba(0,0,0,0.06)]",
        "dark:shadow-[0_-6px_24px_rgba(0,0,0,0.35)]",
      )}
      style={{ paddingBottom: "max(env(safe-area-inset-bottom), 6px)" }}
    >
      <div className="flex h-14 items-stretch">
        {TABS.map(({ tab, label, Icon }) => {
          const isActive = activeTab === tab;
          return (
            <button
              key={tab}
              type="button"
              aria-label={label}
              aria-pressed={isActive}
              onClick={() => handlePress(tab)}
              className={cn(
                "group relative flex flex-1 flex-col items-center justify-center gap-0.5",
                "transition-all duration-200",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset",
                "active:opacity-60 active:scale-95",
              )}
            >
              <div className={cn(
                "absolute top-0 left-1/2 -translate-x-1/2 h-[2.5px] rounded-b-full transition-all duration-300 ease-out",
                isActive ? "w-8 bg-primary opacity-100" : "w-0 opacity-0",
              )} />
              <div className={cn(
                "flex h-8 w-[52px] items-center justify-center rounded-full transition-all duration-200",
                isActive
                  ? "bg-primary/10 dark:bg-primary/15"
                  : "group-hover:bg-muted/70 group-active:bg-muted",
              )}>
                <Icon className={cn(
                  "h-[18px] w-[18px] transition-all duration-200",
                  isActive ? "text-primary scale-110" : "text-muted-foreground group-hover:text-foreground",
                )} />
              </div>
              <span className={cn(
                "text-[10px] leading-none tracking-wide transition-colors duration-200",
                isActive ? "font-semibold text-primary" : "font-medium text-muted-foreground",
              )}>
                {label}
              </span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}
