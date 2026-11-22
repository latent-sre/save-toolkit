# Stack, design tokens, and API integration

## React toolchain (greenfield default)

- **Core:** React 19.3, Vite 8 (`npm create vite@latest -- --template react-ts`), npm with committed
  lockfile (preserve pnpm where used), Active LTS Node, Tailwind v4 (`@tailwindcss/vite`).
- **TypeScript 7:** Typecheck with `tsc -b` (root `tsconfig.json` uses project references and `files: []`).
  Mirror `@/*` paths in `tsconfig.json`/`tsconfig.app.json` and Vite `resolve.alias` without `baseUrl` (removed in TS 7).
- **Compiler, lint, tests:** React Compiler (`babel-plugin-react-compiler` via `@rolldown/plugin-babel`),
  `oxlint` + `oxlint-tsgolint` (`oxlint --type-aware` for `no-floating-promises` / `no-misused-promises`),
  Prettier, Vitest 5, Testing Library, MSW 3 (`msw/http`, `onUnhandledFrame`; `msw/sse` is browser-only —
  use `ReadableStream` in Node/jsdom), and `axe-core` (disable `color-contrast` in jsdom; check in browser).

## Vue toolchain

Use `npm create vue@latest` when the caller or neighboring apps use Vue. Keep TypeScript 6.0.x +
`vue-tsc` 3.3 until `vue-tsc` and `typescript-eslint` support TS 7. Default kit: `shadcn-vue`, Reka UI,
Tailwind v4, `motion-v`, `@lucide/vue`, VueUse (Nuxt UI or Vuetify as full alternatives; PrimeVue 5
requires owner licence approval). Use `@tanstack/vue-query`, Vue Router, Pinia (distant shared state only),
`@tanstack/vue-table` v9 (`tableFeatures` + `useTable`), `onErrorCaptured` error panels, and strict
sanitization / protocol allowlists on `v-html` and bound URLs.

## Component kits, mixing, and OKLCH tokens

Approved React kits: **shadcn/ui** (default; Base UI, Radix `-b radix`, or React Aria `-b aria`),
Radix UI, Base UI (`isolation: isolate` on app root), HeroUI v3, Mantine 9 (`styles.layer.css`),
Material UI 9 (`StyledEngineProvider enableCssLayer`), daisyUI 5 (prefix `d-` when mixing), Magic UI,
Animate UI, Aceternity UI, React Bits, and Motion (`motion/react` with `LazyMotion`).

1. Declare CSS layers once before imports (`@layer theme, base, mantine, mui, components, utilities;`)
   so `utilities` wins last; check third-party licences before adding paid/custom kits.
2. Keep one owner per interaction primitive (dialogs/modals, tooltips, toasts, icons, dates) to avoid
   competing focus traps and portals.
3. Derive light and dark tokens in OKLCH using `light-dark()` from brief knobs (`--brand-hue`,
   `--surface-hue`, `--density`, `--font-ui`, `--font-code`) with fixed status hues (`ok`, `warn`,
   `critical`, `info`, `unknown`) kept separate from brand and categorical chart colors.

## Data, typed clients, and API integration

- **Typed client:** Generate from OpenAPI (`openapi-typescript` + `openapi-fetch` or `@hey-api/openapi-ts`).
  Isolate OpenAPI codegen in a separate TS 5 tooling package because TS 7 dropped the classic compiler
  API. Verify generators handle OpenAPI 3.2 streaming `itemSchema` rather than typing streams as `unknown`.
- **Server state, routing, tables, forms:** TanStack Query 5 (`queryOptions`; include path, filters,
  sort, cursor, and user/tenant scope in keys; render `dataUpdatedAt` and stale banners), TanStack Router
  + Zod 4 (or React Router + `nuqs`), TanStack Table 9 (`tableFeatures` + `useTable`, memoizing `features`,
  `columns`, and empty arrays; `useReactTable`/`useVueTable` removed) + TanStack Virtual,
  `react-hook-form` or TanStack Form + Zod 4, `date-fns 4` + `@date-fns/tz`.
- **Errors & cursor pages:** With `openapi-fetch`, parse error bodies from `{ error, response }` (stream
  already consumed); read `X-Request-ID` and map field errors (`errors[].loc` or FastAPI `detail[].loc`)
  preserving user input. Pass `next_cursor` verbatim as `?cursor=` and deduplicate appended rows by ID.
- **Idempotent writes:** Match the backend contract (native idempotence, `If-Match` → `412`, or
  `Idempotency-Key` generated per user intent and reused on unchanged retries, waiting out `409` +
  `Retry-After` up to `maxWaitMs`). Snapshot mutable/multipart bodies once before retrying.
- **Live data & sessions:** Default to polling; use SSE (fetch-based `eventsource` for bearer auth,
  never tokens in URLs) or WebSocket with one reconnect owner, capped jittered backoff, and
  `requestAnimationFrame`-batched updates. Keep OIDC tokens server-side in `Secure`/`HttpOnly`/`SameSite`
  cookies (or memory-only if JS must hold bearer tokens). On logout/identity switch, cancel in-flight
  requests, close streams, clear/re-scope cache, and notify other tabs via `BroadcastChannel`.
