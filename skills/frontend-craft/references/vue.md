# Vue

Use Vue when the caller or neighbouring apps choose it. The parent skill and
[design](./design.md), [API](./api.md) and [serving](./serving.md) contracts apply; this reference
supplies the framework equivalents.

## Toolchain

Vue 3.5, TypeScript and Vite: `npm create vue@latest` with TypeScript, Router, Vitest and ESLint;
add Pinia only when shared UI state needs it. Keep Vue 3.6/Vapor out of production until stable.
Use `<script setup lang="ts">` components with `defineModel`, `useTemplateRef` and
`onWatcherCleanup`. Pin TypeScript 6 while `vue-tsc` needs its compiler API, checking
compatibility before upgrading. Use Node 22.12 or later, ESLint flat config with
`eslint-plugin-vue` and `@vue/eslint-config-typescript` type-checked rules, Vitest,
Vue Test Utils and MSW.

## Kits

Default: **shadcn-vue**, **Reka UI**, **Tailwind v4**, **motion-v**, **@lucide/vue** and
**VueUse** composables, all MIT. Optional animated collections: **Inspira UI** (Aceternity/Magic
designs sharing shadcn-vue tokens) and **Vue Bits**. Full-system alternatives: **Nuxt UI**
(Reka/Tailwind, MIT, supports plain Vite) and **Vuetify** (MIT; follow its Tailwind guide because
it owns a reset). **PrimeVue 5** has its own licence requiring a licence decision.
Apply the [stack mixing rules](./stack.md#mixing-kits) and shared theme tokens.

## Data and interactions

- **@tanstack/vue-query** with `openapi-fetch` calls wrapped in `queryOptions`; **orval** or
  **kubb** for generated composables. There is no official Vue OpenAPI-query wrapper.
- **Vue Router** for routes/shareable URL state; **Pinia** for distant components' shared UI
  state, leaving server data in the query cache.
- **TanStack Table**'s Vue adapter and **TanStack Virtual**; **VeeValidate** or **TanStack Form**
  with Zod 4; **date-fns 4** and **@date-fns/tz**; **vue-echarts**; **@vue-flow/core**.
- **Error boundaries:** use `onErrorCaptured` for a region's error panel and stop propagation;
  `app.config.errorHandler` reports uncaught failures. Port the React error card's markup.
- **Untrusted content:** only sanitized HTML reaches `v-html`; bound `:href`/`:src` values
  pass the parent skill's protocol allowlist.
