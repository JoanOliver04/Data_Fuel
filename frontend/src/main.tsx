import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import { createLogger } from "./lib/logger";
import "./styles/index.css";

const log = createLogger("app");

// Catch render-path errors and async failures that escape React's boundaries.
window.addEventListener("error", (event) => {
  log.error("uncaught error", event.error ?? event.message, {
    source: event.filename,
    line: event.lineno,
    col: event.colno,
  });
});

window.addEventListener("unhandledrejection", (event) => {
  log.error("unhandled promise rejection", event.reason);
});

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Root element #root not found in index.html");
}

log.info("app boot", {
  mode: import.meta.env.MODE,
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? "(proxy)",
});

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
