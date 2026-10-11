# Vue

Read for any Vue app. Vue is allowed and React is the focus: an existing Vue app keeps Vue, and a
new app is Vue when the caller or its neighbouring apps say so. The universal rules live in the
parent file, and the [design](./design.md), [API](./api.md) and [serving](./serving.md) references
apply unchanged; this file names the Vue equivalents of the stack.

## A new Vue app

Vue 3.5 with TypeScript on Vite, scaffolded with `npm create vue@latest` (TypeScript, Router,
Vitest, ESLint; Pinia only once a store is needed); Vue 3.6 and Vapor mode stay out of production
until Vue marks them stable. `<script setup lang="ts">` single-file components with `defineModel`,
`useTemplateRef` and `onWatcherCleanup`. `vue-tsc` needs the TypeScript compiler API, so pin
`typescript@6` for the same reason the React stack does. ESLint flat config with
`eslint-plugin-vue` and `@vue/eslint-config-typescript`'s type-checked rules; Vitest, Vue Test
Utils and MSW; Node 22.12 or later.

## Kits

The default base is **shadcn-vue** on **Reka UI** primitives with **Tailwind v4** and **motion-v**
as the animation engine, all MIT; `@lucide/vue` for icons; **VueUse** for utility composables
(`useEventSource`, `useStorage`, `useDark`). For the signature moment, **Inspira UI** (the
Aceternity and Magic UI designs ported to Vue, sharing shadcn-vue's tokens) and **Vue Bits**. Full
systems a repository or caller may choose instead: **Nuxt UI** (Reka UI and Tailwind, MIT, works in
a plain Vite app) and **Vuetify** (MIT, its own reset, so follow its Tailwind guide); **PrimeVue 5**
carries its own licence, so it needs a licence decision first. The theme file and the mixing
rules in the [stack reference](./stack.md) apply unchanged.

## Data, routing and forms

`@tanstack/vue-query` wrapping `openapi-fetch` calls in `queryOptions` (there is no official Vue
wrapper for the OpenAPI client; `orval` or `kubb` generate composables when they are wanted);
**Vue Router** with filters and views in the URL; **Pinia** only for state two distant components
genuinely share, with server data staying in the query cache; TanStack Table's Vue adapter with
TanStack Virtual; **VeeValidate** or TanStack Form with a Zod 4 schema; date-fns 4 with
`@date-fns/tz`; ECharts through `vue-echarts`; `@vue-flow/core` for graphs.

## Vue-specific rules

- **Error boundaries:** a boundary component uses `onErrorCaptured` to render its panel's error
  card and stop propagation; `app.config.errorHandler` reports what no boundary handled. The
  React error panel's card markup ports directly.
- **Untrusted content:** `v-html` takes only sanitized output, and a bound `:href` or `:src`
  passes the protocol allowlist before it renders.
- **Vue 2** is past end of life: keep its stack for a feature change and name the upgrade as a
  separate decision.
