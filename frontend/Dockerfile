# syntax=docker/dockerfile:1.6
#
# Production image for the Data Fuel React frontend.
#
# Stage 1 (builder)  — Node 20 Alpine, npm ci against the lockfile, then a
# full Vite build (tsc -b && vite build). Only the resulting static bundle
# survives into the runtime image.
#
# Stage 2 (runtime)  — Nginx Alpine serving the compiled bundle. The bundled
# SPA fallback and /api proxy live in nginx.conf so React Router deep links
# and same-origin API calls just work behind the compose network.

# ─── Stage 1: builder ────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /build

# Lockfile-driven install: keeps the dependency tree byte-identical to CI.
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY . .
RUN npm run build

# ─── Stage 2: runtime ────────────────────────────────────────────────────────
FROM nginx:1.27-alpine AS runtime

LABEL org.opencontainers.image.title="datafuel-frontend" \
      org.opencontainers.image.description="Data Fuel React/Vite SPA served by nginx" \
      org.opencontainers.image.source="https://github.com/JoanOliver04/Data_Fuel" \
      org.opencontainers.image.licenses="PolyForm-Noncommercial-1.0.0"

# Drop the default site and replace with our SPA + /api proxy config.
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf

COPY --from=builder /build/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --quiet --spider http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
