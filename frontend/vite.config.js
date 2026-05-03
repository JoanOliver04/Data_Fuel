/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";
import path from "node:path";
import { pwaManifest } from "./src/features/pwa/manifest";
export default defineConfig({
    plugins: [
        react(),
        VitePWA({
            registerType: "autoUpdate",
            includeAssets: [
                "favicon.svg",
                "favicon.ico",
                "apple-touch-icon-180x180.png",
                "pwa-64x64.png",
                "pwa-192x192.png",
                "pwa-512x512.png",
                "maskable-icon-512x512.png",
                "screenshot-wide.png",
                "screenshot-narrow.png",
            ],
            manifest: pwaManifest,
            workbox: {
                globPatterns: ["**/*.{js,css,html,svg,png,ico,webmanifest,woff,woff2}"],
                navigateFallback: "/offline.html",
                navigateFallbackDenylist: [/^\/api\//],
                runtimeCaching: [
                    {
                        urlPattern: function (_a) {
                            var url = _a.url;
                            return url.pathname.startsWith("/api/v1/");
                        },
                        handler: "NetworkFirst",
                        options: {
                            cacheName: "datafuel-api-v1",
                            networkTimeoutSeconds: 4,
                            expiration: {
                                maxEntries: 100,
                                maxAgeSeconds: 60 * 60 * 24,
                            },
                            cacheableResponse: { statuses: [0, 200] },
                        },
                    },
                    {
                        urlPattern: function (_a) {
                            var request = _a.request;
                            return request.destination === "script" ||
                                request.destination === "style" ||
                                request.destination === "worker";
                        },
                        handler: "CacheFirst",
                        options: {
                            cacheName: "datafuel-static-assets",
                            expiration: {
                                maxEntries: 60,
                                maxAgeSeconds: 60 * 60 * 24 * 30,
                            },
                        },
                    },
                    {
                        urlPattern: function (_a) {
                            var request = _a.request;
                            return request.destination === "font";
                        },
                        handler: "CacheFirst",
                        options: {
                            cacheName: "datafuel-fonts",
                            expiration: {
                                maxEntries: 30,
                                maxAgeSeconds: 60 * 60 * 24 * 365,
                            },
                            cacheableResponse: { statuses: [0, 200] },
                        },
                    },
                    {
                        urlPattern: /^https:\/\/fonts\.(?:googleapis|gstatic)\.com\/.*/,
                        handler: "CacheFirst",
                        options: {
                            cacheName: "datafuel-google-fonts",
                            expiration: {
                                maxEntries: 20,
                                maxAgeSeconds: 60 * 60 * 24 * 365,
                            },
                            cacheableResponse: { statuses: [0, 200] },
                        },
                    },
                ],
            },
            devOptions: {
                enabled: true,
                type: "module",
                navigateFallback: "/index.html",
            },
        }),
    ],
    envDir: "..",
    resolve: {
        alias: {
            "@": path.resolve(__dirname, "./src"),
        },
    },
    server: {
        port: 5173,
        proxy: {
            "/api": {
                target: "http://localhost:8000",
                changeOrigin: true,
            },
        },
    },
    preview: {
        port: 4173,
        proxy: {
            "/api": {
                target: "http://localhost:8000",
                changeOrigin: true,
            },
        },
    },
    build: {
        outDir: "dist",
        sourcemap: true,
        target: "es2022",
        rollupOptions: {
            output: {
                // Split heavy third-party libs into cacheable chunks. Browsers fetch
                // them in parallel, and unchanged vendors stay cached across deploys.
                manualChunks: {
                    "react-vendor": ["react", "react-dom", "react-router-dom"],
                    leaflet: ["leaflet", "react-leaflet"],
                    recharts: ["recharts"],
                    radix: [
                        "@radix-ui/react-dialog",
                        "@radix-ui/react-dropdown-menu",
                        "@radix-ui/react-label",
                        "@radix-ui/react-slot",
                        "@radix-ui/react-tooltip",
                    ],
                    query: ["@tanstack/react-query"],
                },
            },
        },
    },
    test: {
        globals: true,
        environment: "jsdom",
        setupFiles: ["./src/test/setup.ts"],
    },
});
