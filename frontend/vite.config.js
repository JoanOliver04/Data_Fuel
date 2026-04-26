/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";
export default defineConfig({
    plugins: [react()],
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
