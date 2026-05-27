import { BarChart3, BrainCircuit, ChevronDown, X } from "lucide-react";
import { Suspense, lazy, useState } from "react";

import { cn } from "@/lib/utils";

import { useXaiExplanation } from "../hooks";
import type { ExplainRecommendationRequest } from "../types";
import { AiReasoningBlock } from "./AiReasoningBlock";
import { ShapImpactList } from "./ShapImpactList";

// Recharts (~300 KB) loads only when the user opens the global-importance panel.
const FeatureImportanceChart = lazy(() =>
  import("./FeatureImportanceChart").then((m) => ({ default: m.FeatureImportanceChart })),
);

interface AiExplainabilityCardProps {
  params: ExplainRecommendationRequest;
  onDismiss?: () => void;
}

function CardShell({
  children,
  onDismiss,
}: {
  children: React.ReactNode;
  onDismiss?: (() => void) | undefined;
}) {
  return (
    <div className="animate-in fade-in-0 slide-in-from-top-2 relative space-y-3 rounded-xl border-2 border-violet-200 bg-violet-50/60 p-4 duration-300 dark:border-violet-800/50 dark:bg-violet-950/20">
      <div className="flex items-center gap-1.5">
        <BrainCircuit className="h-4 w-4 text-violet-600 dark:text-violet-400" />
        <span className="text-[10px] font-bold uppercase tracking-widest text-violet-700 dark:text-violet-300">
          Explicabilidad IA · SHAP
        </span>
        {onDismiss && (
          <button
            onClick={onDismiss}
            aria-label="Cerrar explicación"
            className="absolute right-3 top-3 rounded-full p-0.5 text-muted-foreground/50 hover:text-muted-foreground"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        )}
      </div>
      {children}
    </div>
  );
}

/**
 * Premium explainability panel. On render it fetches the local SHAP explanation
 * for the active recommendation and shows: the deterministic reasoning, the
 * per-factor SHAP impacts (green lowers / red raises the predicted price), and —
 * lazily — the model's global feature-importance chart.
 *
 * Fully self-degrading: a loading skeleton while in flight, a quiet inline notice
 * on error, and a graceful "SHAP unavailable" path driven by the API contract.
 */
export function AiExplainabilityCard({ params, onDismiss }: AiExplainabilityCardProps) {
  const { data, isLoading, isError } = useXaiExplanation(params);
  const [showChart, setShowChart] = useState(false);

  if (isLoading) {
    return (
      <CardShell onDismiss={onDismiss}>
        <div className="space-y-2" aria-label="Generando explicación">
          <div className="h-4 w-2/3 animate-pulse rounded bg-violet-200/60 dark:bg-violet-800/40" />
          <div className="h-3 w-full animate-pulse rounded bg-violet-200/50 dark:bg-violet-800/30" />
          <div className="h-3 w-5/6 animate-pulse rounded bg-violet-200/50 dark:bg-violet-800/30" />
          <div className="h-16 w-full animate-pulse rounded bg-violet-200/40 dark:bg-violet-800/20" />
        </div>
      </CardShell>
    );
  }

  if (isError || !data) {
    return (
      <CardShell onDismiss={onDismiss}>
        <p className="text-xs text-muted-foreground">
          No se pudo generar la explicación de la IA en este momento.
        </p>
      </CardShell>
    );
  }

  return (
    <CardShell onDismiss={onDismiss}>
      <AiReasoningBlock
        reasoning={data.reasoning}
        veredicto={data.veredicto}
        confidence={data.confidence}
      />

      {data.shap_available ? (
        <div className="space-y-2 border-t border-violet-200/70 pt-3 dark:border-violet-800/40">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
              Factores de esta predicción
            </span>
            <span className="text-[10px] tabular-nums text-muted-foreground">
              base {data.base_value.toFixed(3)} → {data.prediction.toFixed(3)} €/L
            </span>
          </div>
          <ShapImpactList factors={data.feature_importance_local} />
        </div>
      ) : (
        <p className="border-t border-violet-200/70 pt-3 text-[11px] text-muted-foreground dark:border-violet-800/40">
          Desglose SHAP no disponible; se muestran los factores globales del modelo.
        </p>
      )}

      <div className="border-t border-violet-200/70 pt-2 dark:border-violet-800/40">
        <button
          onClick={() => setShowChart((v) => !v)}
          aria-expanded={showChart}
          className="flex w-full items-center justify-between text-xs font-semibold text-violet-700 hover:text-violet-900 dark:text-violet-300 dark:hover:text-violet-100"
        >
          <span className="flex items-center gap-1.5">
            <BarChart3 className="h-3.5 w-3.5" />
            Importancia global del modelo
          </span>
          <ChevronDown
            className={cn("h-4 w-4 transition-transform", showChart && "rotate-180")}
          />
        </button>
        {showChart && (
          <div className="mt-2">
            <Suspense
              fallback={
                <div className="h-40 w-full animate-pulse rounded bg-violet-200/40 dark:bg-violet-800/20" />
              }
            >
              <FeatureImportanceChart features={data.feature_importance_global} />
            </Suspense>
          </div>
        )}
      </div>
    </CardShell>
  );
}
