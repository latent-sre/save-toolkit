# Vue

Use Vue when selected by the caller or neighbouring apps; shared [design](./design.md),
[API](./api.md) and [serving](./serving.md) contracts apply.

## Toolchain

For a new app, use `npm create vue@latest` with TypeScript, Router, Vitest and ESLint.
Keep the scaffold's compatible TypeScript and `vue-tsc` pair (TypeScript 6.0.x with
`vue-tsc` 3.3). Before a compiler upgrade, confirm support in both `vue-tsc` and
`typescript-eslint` and run the project's Vue single-file-component typecheck and typed lint.
Use Active LTS Node within the scaffold's engines, ESLint flat config (`eslint-plugin-vue`,
`@vue/eslint-config-typescript`), Vitest, Vue Test Utils and MSW. Existing apps keep their
locked tools for feature edits.

## Kits

Default: **shadcn-vue**, **Reka UI**, **Tailwind v4**, **motion-v**, **@lucide/vue** (ISC) and
**VueUse** (others MIT). Optional animated collections: **Inspira UI** and **Vue Bits**. Full-system
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
