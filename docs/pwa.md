# Progressive Web App

Data Fuel ships as an installable, offline-resilient PWA: a real mobile fuel
assistant users can keep on their home screen. It is built on `vite-plugin-pwa`
(Workbox `generateSW`) with `registerType: "autoUpdate"`, so a new version
activates and reloads on its own.

- [Architecture](#architecture)
- [Caching strategy](#caching-strategy)
- [Offline strategy](#offline-strategy)
- [Install experience](#install-experience)
- [Observability](#observability)
- [Push-notification roadmap](#push-notification-roadmap)
- [Install instructions](#install-instructions)

## Architecture

```
frontend/src/features/pwa/
├── manifest.ts              # Web App Manifest (consumed by vite.config.ts)
├── registerPWA.ts           # SW registration + lifecycle telemetry (main.tsx)
├── usePWA.ts                # install-prompt + standalone-mode hooks
├── InstallPrompt.tsx        # contextual install banner (rendered on Home)
├── StandaloneBadge.tsx      # "installed app" affordance
├── useOnlineStatus.ts       # reactive online/offline (useSyncExternalStore)
├── OfflineBanner.tsx        # global offline banner (rendered in App)
├── useNotificationPermission.ts  # push-ready permission flow (no subscribe yet)
└── telemetry.ts             # structured PWA event logging
```

The SW + manifest are configured in `vite.config.ts`. **Note:** `tsconfig.node.json`
is composite and emits to `node_modules/.tmp` — never beside the sources — so
`tsc -b` cannot create stale `vite.config.js` / `manifest.js` twins that would
shadow the `.ts` at resolve time. `frontend/dev-dist/` (dev SW output) is
git-ignored.

## Caching strategy

Workbox precaches the app shell + static assets (`globPatterns`), with runtime
strategies tuned so **dynamic data stays fresh**:

| Request | Strategy | Why |
| --- | --- | --- |
| `/api/v1/*` (prices, recommendations, predictions, routing) | **NetworkFirst** (4 s timeout, 1-day cap) | live data must be fresh; cache is only a last-resort offline fallback |
| scripts / styles / workers | CacheFirst (30-day) | content-hashed, safe to cache long |
| fonts (local + Google) | CacheFirst (1-year) | immutable |
| navigations | precached shell, `navigateFallback: /offline.html`, `denylist: /api/` | shell loads offline; API never serves the SPA fallback |

Recommendation/prediction/traffic responses are **never** cache-first — they go
through NetworkFirst and fall back to cache only when the network fails.

## Offline strategy

- `useOnlineStatus` tracks connectivity via `online`/`offline` events.
- `OfflineBanner` (global, in `App`) shows "Sin conexión — mostrando los últimos
  datos en caché" and is safe-area aware for installed iOS.
- The cached shell keeps the app navigable offline; cached API reads still
  render. The SW failing to register **never breaks the app** (`registerPWA` is
  fully guarded).
- `public/offline.html` is the navigation fallback for uncached routes.

## Install experience

`useInstallPrompt` captures `beforeinstallprompt`, and `InstallPrompt` shows a
subtle, dismissible banner. Dismissal is persisted
(`localStorage: datafuel:v1:pwa-install-dismissed`) so users are not nagged.
`useStandaloneMode` detects launched-as-app for tailored UI. iOS has no
`beforeinstallprompt`, so it relies on the manual Share → Add to Home Screen flow
(see below).

## Observability

`telemetry.ts` logs structured events via the app logger (`pwa:*`):
`install_prompt_shown`, `install_accepted`, `install_dismissed`,
`offline_entered`, `offline_exited`, `sw_registered`, `sw_offline_ready`,
`sw_updated`, `sw_register_failed`, `sw_cache_error`, `notification_permission`.
These are console-visible today and trivially forwarded to a real sink later.

## Push-notification roadmap

`useNotificationPermission` ships the permission flow only — it does **not**
subscribe to push yet. The integration seam: once permission is `granted`, add
`registration.pushManager.subscribe()` and POST the subscription to a backend
endpoint, then wire it to the [intelligent alerts](alerts.md) engine (threshold
hits, weekly summaries, prediction signals). The SW already exists; switching
`generateSW` → `injectManifest` later would allow custom `push`/`notificationclick`
handlers without touching the rest of the architecture.

## Install instructions

**Android (Chrome/Edge):** open the site → tap the **Install** banner, or menu
(⋮) → **Install app / Add to Home screen**.

**iPhone/iPad (Safari):** **Share** (□↑) → **Add to Home Screen** → **Add**.
(iOS does not support automatic install prompts.)

**Desktop (Chrome/Edge):** click the **install icon** in the address bar, or
menu → **Install Data Fuel**.

Once installed it launches standalone (no browser chrome), portrait, with the
themed splash + icons from the manifest.
