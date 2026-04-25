/**
 * Tiny namespaced logger used across the frontend.
 *
 * In dev (`import.meta.env.DEV`) every level prints. In production the bar
 * raises to WARN so users never see verbose output but errors still surface
 * in the browser console for support.
 *
 * Usage:
 *     const log = createLogger("api");
 *     log.info("recommendations request", { lat, lon });
 *     log.error("recommendations failed", err);
 */

type Level = "debug" | "info" | "warn" | "error";

const LEVELS: Record<Level, number> = { debug: 10, info: 20, warn: 30, error: 40 };

const MIN_LEVEL: number = import.meta.env.DEV ? LEVELS.debug : LEVELS.warn;

const STYLES: Record<Level, string> = {
  debug: "color:#888",
  info: "color:#0a7",
  warn: "color:#c80",
  error: "color:#e44;font-weight:bold",
};

function emit(level: Level, scope: string, args: unknown[]): void {
  if (LEVELS[level] < MIN_LEVEL) return;
  const tag = `%c[${level.toUpperCase()}] ${scope}`;
  const fn = level === "debug" ? console.debug
    : level === "info" ? console.info
    : level === "warn" ? console.warn
    : console.error;
  fn(tag, STYLES[level], ...args);
}

export interface Logger {
  debug: (...args: unknown[]) => void;
  info: (...args: unknown[]) => void;
  warn: (...args: unknown[]) => void;
  error: (...args: unknown[]) => void;
}

export function createLogger(scope: string): Logger {
  return {
    debug: (...args) => emit("debug", scope, args),
    info: (...args) => emit("info", scope, args),
    warn: (...args) => emit("warn", scope, args),
    error: (...args) => emit("error", scope, args),
  };
}
