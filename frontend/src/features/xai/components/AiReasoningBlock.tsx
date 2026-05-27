import { CheckCircle, Clock } from "lucide-react";

import { cn } from "@/lib/utils";

interface AiReasoningBlockProps {
  reasoning: string;
  veredicto: "REPOSTA AHORA" | "ESPERA";
  confidence: number;
}

/** Splits the engine's "lead:\n- bullet.\n- bullet." text into parts. */
function parseReasoning(reasoning: string): { lead: string; bullets: string[] } {
  const lines = reasoning.split("\n").map((l) => l.trim()).filter(Boolean);
  const lead = lines[0] ?? reasoning;
  const bullets = lines.slice(1).map((l) => l.replace(/^[-•]\s*/, ""));
  return { lead, bullets };
}

/**
 * Natural-language reasoning generated deterministically from the SHAP
 * attribution (no LLM). Shows the verdict, the model's confidence, and the
 * human-readable "why".
 */
export function AiReasoningBlock({ reasoning, veredicto, confidence }: AiReasoningBlockProps) {
  const isRefuelNow = veredicto === "REPOSTA AHORA";
  const confidencePct = Math.round(Math.max(0, Math.min(1, confidence)) * 100);
  const { lead, bullets } = parseReasoning(reasoning);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <span
          className={cn(
            "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-bold",
            isRefuelNow
              ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400"
              : "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400",
          )}
        >
          {isRefuelNow ? <CheckCircle className="h-3.5 w-3.5" /> : <Clock className="h-3.5 w-3.5" />}
          {veredicto}
        </span>
        <span className="text-xs text-muted-foreground">
          Confianza <span className="font-semibold tabular-nums text-foreground">{confidencePct}%</span>
        </span>
      </div>

      <p className="text-sm leading-relaxed text-foreground/80">{lead}</p>

      {bullets.length > 0 && (
        <ul className="space-y-1">
          {bullets.map((b, i) => (
            <li key={i} className="flex gap-2 text-sm text-foreground/75">
              <span
                className={cn(
                  "mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full",
                  isRefuelNow ? "bg-emerald-500" : "bg-amber-500",
                )}
                aria-hidden="true"
              />
              <span>{b}</span>
            </li>
          ))}
        </ul>
      )}

      <div className="h-1.5 overflow-hidden rounded-full bg-black/10 dark:bg-white/10">
        <div
          className={cn(
            "h-full rounded-full transition-all duration-700 ease-out",
            isRefuelNow ? "bg-emerald-500" : "bg-amber-500",
          )}
          style={{ width: `${confidencePct}%` }}
        />
      </div>
    </div>
  );
}
