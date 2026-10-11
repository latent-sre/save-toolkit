# Vue

Read for any Vue app. An existing app's libraries, router, store and conventions win; the
choices below are for a new Vue app and for capabilities an app does not have yet. The universal
rules live in `../SKILL.md`; on any conflict, SKILL.md wins.

## A new Vue app

**Vue 3 + TypeScript single-page app on Vite**, scaffolded with `npm create vue@latest`
(TypeScript, Router, Pinia, Vitest, ESLint), with only the dependencies its features need. Use
the stable 3.5 line; Vue 3.6 and Vapor mode are release candidates, not for production until Vue
marks them stable. `<script setup lang="ts">` single-file components with `defineModel` for
two-way props, `useTemplateRef` for typed refs and `onWatcherCleanup` for subscriptions. Pin
`typescript` to 6.x: `vue-tsc` and typescript-eslint both need the compiler API TypeScript 7
dropped. ESLint flat config with `eslint-plugin-vue` and `@vue/eslint-config-typescript`'s
type-checked rules. Vitest, Vue Test Utils and MSW; Playwright only with the caller's approval.
Node 22 or later. If the user explicitly asks for plain HTML or a static page, comply; record any
other framework or library choice for a new app in the review packet.

## The component system

A new Vue app starts from **shadcn-vue** on **Reka UI** primitives (formerly Radix Vue) with
**Tailwind v4** through `@tailwindcss/vite` and **motion-v** as the animation engine; `@lucide/vue`
for icons (formerly `lucide-vue-next`). The Vue collections layer on that stack: **Inspira UI**
(MIT; the Aceternity and Magic UI designs ported to Vue, sharing shadcn-vue's tokens) and
**Vue Bits** (MIT plus Commons Clause); name the licence in the review packet. **Nuxt UI** (Reka
UI + Tailwind, works in a plain Vite app) and **Vuetify** (its own reset; follow its Tailwind
guide) are full systems a repository or caller may choose instead; PrimeVue 5 is no longer MIT,
so it needs a licence decision first. One system per app, never two.

## Data, routing and forms

**TanStack Query** (`@tanstack/vue-query`) for server state, wrapping the typed client in
`queryOptions` — there is no official OpenAPI wrapper for Vue, so write thin composables, or use
`orval` or `kubb` when generated composables are wanted. **Vue Router 5** for routes, including
typed file-based routing, with filters and views in the URL. **Pinia** only for state two distant
components genuinely share — server data stays in the query cache, derived with `computed`, never
copied into a store. **TanStack Table**'s Vue adapter (v9) for grids with **TanStack Virtual**.
**VeeValidate** or **TanStack Form** with a Standard Schema (**Zod 4**) for forms, `v-model` plus
the repository's validation layer for simple ones. **VueUse** for utility composables such as
`useEventSource`, `useStorage` and `useDark`. **date-fns** v4 with `@date-fns/tz` for times.

## Capabilities — what to reach for

| Capability | Vue libraries | Platform |
|---|---|---|
| Live data | VueUse `useEventSource` for cookie-authenticated SSE, the `eventsource` package when headers are needed; native WebSocket with your own backoff; events land in the query cache | `BroadcastChannel` + Web Locks: one tab owns the socket |
| Dense data | TanStack Table + Virtual; Perspective or AG Grid for streaming grids past ~100k rows | `content-visibility` on long logs; the WAI-ARIA grid keyboard model |
| Navigation and keys | shadcn-vue's Command, VueUse `useMagicKeys`, resizable panes from the system | — |
| Motion | motion-v for orchestrated moments; `<Transition>` for element enter/exit | `@starting-style`, `transition-behavior: allow-discrete`, `prefers-reduced-motion` |
| Charts | ECharts through `vue-echarts` for dashboards; uPlot for streaming series | — |
| Editing and text | CodeMirror 6 for in-app query editors; `markdown-it` + DOMPurify; `shiki`; `@xterm/xterm` 6; TanStack Virtual for log tails; `anser` for ANSI colour | `field-sizing: content` |
| Graphs | `@vue-flow/core`; layout with `d3-force` or `elkjs` (EPL/GPL dual licence — check policy) | — |
| Notifications | the system's toast | Web Push through a service worker; iOS needs a Home Screen install |
| Dialogs and menus | Reka UI primitives | `<dialog>`, `popover`, `inert`; anchor positioning is not Baseline yet |

## Vue-specific rules

- **Error boundaries:** a boundary component uses `onErrorCaptured` to render its panel's inline
  error card and stop propagation; `app.config.errorHandler` reports what no boundary handled.
- **Untrusted content:** `v-html` takes only sanitized output, and a bound `:href` or `:src`
  passes the protocol allowlist before it renders.
- **Vue 2:** a Vue 2 app is past end of life; keep its stack for a feature change and name the
  upgrade as a separate decision.
