# React

Read for any React app. An existing app's libraries, router and conventions win; the choices
below are for a new React app and for capabilities an app does not have yet. The universal rules
live in `../SKILL.md`; on any conflict, SKILL.md wins.

## A new React app

**React 19 + TypeScript single-page app on Vite**, with only the dependencies its features need.
TypeScript `strict`, no `any`, `unknown` narrowed at the boundary; pin `typescript` to 6.x while
TypeScript 7 ships no compiler API, because typescript-eslint's type-checked rules
(`no-floating-promises`, `no-misused-promises`, in ESLint flat config) need one. Turn on the React
Compiler (`babel-plugin-react-compiler`, stable since 1.0) instead of hand-written memoization.
Vitest, React Testing Library and MSW at the network boundary; Playwright for the few critical
journeys only with the caller's approval. Node 22 or later.

## The component system — the caller picks one

Ask the caller which of the two defaults a new app starts from, and record the answer:

- **shadcn/ui + Tailwind v4 + Motion.** Copied components on Base UI primitives (shadcn's
  default; Radix and React Aria variants exist), tokens as CSS custom properties in Tailwind's
  `@theme`. The command menu (`cmdk`), toasts (`sonner`), date picker and TanStack Table
  integration come through the same registry, as do the animated collections.
- **HeroUI v3 + Motion.** React Aria behaviour with Tailwind v4 styling: `@heroui/react` plus
  `@heroui/styles` imported after `tailwindcss`, no provider, React 19 or later.

Either way **Motion** (`motion/react`; formerly Framer Motion) is the animation engine, loaded
through `LazyMotion` to keep the bundle small, and CSS handles hovers, fades and enter/exit.
The animated collections — Magic UI and Animate UI (MIT), Aceternity (its own licence: use and
ship, never redistribute), React Bits (MIT plus Commons Clause) — install through the shadcn
registry (`npx shadcn add @magicui/<item>`) and expect shadcn's `cn` helper and token names, so
they belong to the shadcn stack; HeroUI defines the same token names itself and has no recipe
for them. Spend a collection on the one orchestrated moment the design brief allows, and name
its licence and maintenance state in the review packet. Mantine (its own CSS in `@layer
mantine`, `MantineProvider`, React 19.2 or later; with Tailwind, import `styles.layer.css` and
declare the layer order) and Blueprint (built for dense desktop-style data applications; its own
unlayered reset, so not beside Tailwind) are full systems a repository or caller may choose
instead. One system per app, never two.

## Data, routing and forms

**TanStack Query** with `openapi-react-query` for server state; **TanStack Router** for a new
app's routes — typed, with schema-validated search params so every filter is a shareable saved
view (`nuqs` does the same for an app on React Router); **TanStack Table** v9 (features imported
explicitly) with **TanStack Virtual** for grids; **TanStack Form** or **react-hook-form** with a
Standard Schema resolver over **Zod 4**; **date-fns** v4 with `@date-fns/tz` for zone-correct
times (Temporal is not Baseline yet). React 19 Actions — `useActionState`, `useOptimistic`,
`<form action>` — carry pending, optimistic and error state for operator actions;
`useEffectEvent` reads fresh props inside a subscription without re-subscribing; `<Activity>`
keeps a hidden tab mounted with its state; `<ViewTransition>` (stable in 19.3) animates
navigation and list changes on top of the browser's View Transitions API.

## Capabilities — what to reach for

| Capability | React libraries | Platform |
|---|---|---|
| Live data | `eventsource` (fetch-based SSE with auth headers), native WebSocket with your own backoff; events land in the query cache | `BroadcastChannel` + Web Locks: one tab owns the socket, the rest listen |
| Dense data | TanStack Table + Virtual; for streaming grids past ~100k rows, Perspective (`@perspective-dev/react`, WebAssembly, Apache-2.0) or AG Grid (Community is MIT; Enterprise is licensed) | `content-visibility` on long logs; the WAI-ARIA grid keyboard model (one tab stop, arrow keys) |
| Navigation and keys | `cmdk` palette, `react-hotkeys-hook`, `react-resizable-panels`, a `?` shortcut sheet | — |
| Motion | Motion for orchestrated moments; `<ViewTransition>` | `@starting-style` and `transition-behavior: allow-discrete` for dialog, popover and toast enter/exit; `prefers-reduced-motion` |
| Charts | Recharts for static charts; uPlot for streaming series (60 fps to ~100k in-view points); ECharts for large datasets; visx for a bespoke one-off | — |
| Editing and text | CodeMirror 6 (`@uiw/react-codemirror`, ~120 KB gzipped) for in-app query editors; Monaco only when VS Code parity is worth its size; `react-markdown` + `rehype-sanitize`; `shiki`; `@xterm/xterm` 6; TanStack Virtual or `@melloware/react-logviewer` (MPL-2.0) for log tails; `anser` for ANSI colour | `field-sizing: content` for growing inputs |
| Graphs | `@xyflow/react`; layout with `d3-force`, or `elkjs` (EPL/GPL dual licence — check policy) | — |
| Notifications | `sonner` in-app | Web Push through a service worker to page an operator in a background tab; iOS needs a Home Screen install |
| Dialogs and menus | the system's components | `<dialog>`, `popover`, `inert`; anchor positioning is not Baseline — a JS positioner until it is |

## React-specific rules

- **Error boundaries:** React catches render errors only in a boundary. Use the repository's
  boundary (or `react-error-boundary`) around each route and independent panel; it renders the
  panel's inline error card and resets on retry or navigation. Event-handler and async errors
  are not caught by a boundary — handle them where they occur.
- **Untrusted content:** `dangerouslySetInnerHTML` takes only sanitized output, and a `href`
  built from data passes the protocol allowlist before it renders.
- **Router:** keep the app's router; a feature change never migrates React Router to TanStack
  Router or back.
