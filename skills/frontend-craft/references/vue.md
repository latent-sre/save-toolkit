# Vue

Use Vue when selected by the caller or neighbouring apps; shared [design](./design.md),
[API](./api.md) and [serving](./serving.md) contracts apply.

## Toolchain

Use stable Vue, TypeScript and Vite (`npm create vue@latest` with TypeScript, Router, Vitest and
ESLint); check tool compatibility before upgrades.
Pin TypeScript 6: `vue-tsc` 3.3 fails on TypeScript 7 (`typescript/lib/tsc` is not exported)
despite its `>=5.0.0` peer range, and `@vue/eslint-config-typescript` / `typescript-eslint`
type-checked rules require `<6.1.0`. Check both before upgrading. Use Node
22.12+, ESLint flat config (`eslint-plugin-vue`, `@vue/eslint-config-typescript`), Vitest, Vue
Test Utils and MSW.

## Kits

Default: **shadcn-vue**, **Reka UI**, **Tailwind v4**, **motion-v**, **@lucide/vue** and
**VueUse** (all MIT). Optional animated collections: **Inspira UI** and **Vue Bits**. Full-system
alternatives: **Nuxt UI** (Reka/Tailwind, MIT, supports plain Vite) and **Vuetify** (MIT; follow
its Tailwind layer guide). **PrimeVue 5** uses its own licence requiring owner approval. Apply the
[stack mixing rules](./stack.md#mixing-kits) and shared theme tokens.

## Data and interactions

- **@tanstack/vue-query** with `openapi-fetch` wrapped in `queryOptions` (or **@hey-api/openapi-ts**,
  **orval** or **kubb**).
- **Vue Router** for routes and URL state; **Pinia** only for shared UI state.
- **@tanstack/vue-table** v9 (`tableFeatures` + `useTable`, replacing `useVueTable`) and
  **TanStack Virtual**; **VeeValidate** or **TanStack Form** with Zod 4; **date-fns 4** +
  **@date-fns/tz**; **vue-echarts**; **@vue-flow/core**.
- **Error boundaries & safety:** `onErrorCaptured` renders a region error panel and stops
  propagation; `app.config.errorHandler` reports uncaught failures. Only sanitized HTML reaches
  `v-html`; bound `:href`/`:src` values enforce the protocol allowlist. Keep legacy Vue 2 apps on
  their existing stack for feature edits and flag migration separately.
