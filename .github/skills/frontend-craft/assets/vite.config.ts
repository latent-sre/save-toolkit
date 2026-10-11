// vite.config.ts — a new app's starting configuration (Vite 8, React 19, Tailwind v4, Vitest 5).
// React Compiler through @vitejs/plugin-react's native transform, which needs the optional
// `oxc-transform-react` package installed (`npm i -D oxc-transform-react`); the dev server proxies
// the API prefix to the service running on localhost so the browser sees one origin, as it will on
// PCF. The `@` alias matches `"paths": { "@/*": ["./src/*"] }` in tsconfig (no `baseUrl`: TypeScript 6
// deprecates it).
/// <reference types="vitest/config" />
import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Where the API runs during development: FastAPI's default is 8000, a Go service often 8080.
const API_TARGET = process.env.API_TARGET ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react({ compiler: true }), tailwindcss()],
  resolve: { alias: { "@": path.resolve(import.meta.dirname, "./src") } },
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      // The same prefix the API is reached on in every environment; keep it in sync with config.json.
      "/v1": { target: API_TARGET, changeOrigin: false },
      // Server-sent events stream through the proxy unbuffered; WebSockets need `ws: true`.
      "/v1/stream": { target: API_TARGET, changeOrigin: false, ws: true },
    },
  },
  build: {
    sourcemap: true,
    // Keep assets as files: a data: URI in the bundle needs a looser CSP than 'self'.
    assetsInlineLimit: 0,
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    css: false,
  },
});
