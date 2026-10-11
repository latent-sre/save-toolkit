# Stack: toolchain, kits and libraries

Read for a new app, for any kit or library choice, and before mixing kits. An existing app's
choices win; these are the choices for a new app and for capabilities an app does not have yet.
The versions named are the current majors; check the registry before pinning, and name every
addition with its licence in the packet.

## A new React app

- **Vite 8**, whose bundler is Rolldown, with **React 19.3** and TypeScript `strict`: no `any`,
  `unknown` narrowed at the boundary, branded IDs, exhaustively switched unions. **Node 22.12 or
  later**; 24 is the active LTS line. Scaffold with `npm create vite@latest -- --template react-ts`,
  then write this skill's starting `vite.config.ts` over the generated one.
- **TypeScript.** The latest `typescript` major is 7, the native compiler, and it ships no compiler
  API; typescript-eslint and vue-tsc need that API and support 6.x. Pin `typescript@6` in a new app
  while that holds, and move to 7 when typescript-eslint supports it. The build never depends on the
  TypeScript package: Vite strips types itself, and `tsc --noEmit` is the typecheck. TypeScript 6
  deprecates `baseUrl`, so the `@/*` alias shadcn expects is `"paths": { "@/*": ["./src/*"] }` alone,
  mirrored by a `resolve.alias` in the Vite configuration.
- **React Compiler** from the start, through `react({ compiler: true })` in the Vite React plugin
  with its optional `oxc-transform-react` package installed, instead of hand-written memoization;
  the `eslint-plugin-react-hooks` recommended config carries the compiler's rules.
- **Tailwind CSS v4** through `@tailwindcss/vite`; the theme's `@theme inline` block exposes the
  tokens as utilities. Tailwind handles layout and spacing beside every kit below; only Material UI
  brings a styling engine of its own.
- **ESLint 10** flat config with `typescript-eslint`'s type-checked rules (`no-floating-promises`,
  `no-misused-promises`), `eslint-plugin-react-hooks` and `eslint-plugin-react-refresh`; **Prettier**
  for format. The create-vite template's `lint` script runs `oxlint`, which is a fine fast syntax
  lint to keep; add ESLint for the type-checked promise rules, or use oxlint's type-aware mode where
  a repository already runs it. Biome 2 is acceptable where a repository already runs it.
- **Vitest 5**, **Testing Library**, **MSW 3** at the network boundary and `jsdom`; Vitest's
  browser mode on Playwright for component tests that need layout; **Playwright** for the few
  critical journeys, only with the caller's approval; `vitest-axe` or `@axe-core/playwright` for
  the accessibility pass.
- Package manager: **npm**, the team's choice, with one committed lockfile; pnpm only where a
  repository already uses it.

## Component kits

Any kit below may start an app or join one.

| Kit | What it is | Underneath | Styling | Provider | Licence | Reach for it when |
|---|---|---|---|---|---|---|
| **shadcn/ui** | Components copied into the app through the `shadcn` CLI and its registries | Base UI by default; Radix (`init -b radix`) or React Aria (`-b aria`) selectable | Tailwind v4; tokens as CSS variables | None | MIT | The default base kit, and the registry the animated collections install through |
| **Radix UI** | Unstyled primitives (`radix-ui`) and Radix Themes | — | Yours; Themes brings its own CSS and `<Theme>` | Themes only | MIT | Primitives under hand-styled components; Themes for a quick complete look |
| **Base UI** | Unstyled primitives (`@base-ui/react`) from the MUI team | — | Yours | None; `isolation: isolate` on the app root | MIT | The same role as Radix, with the larger set of modern primitives |
| **HeroUI v3** | Styled components on React Aria Components | React Aria | Tailwind v4; `@import "@heroui/styles"` after Tailwind | None | MIT | A complete, polished kit with React Aria's accessibility and no provider |
| **Mantine 9** | A full system: components, hooks, forms, dates, charts, notifications | Its own | Its own CSS, in `@layer mantine` through `styles.layer.css` | `MantineProvider` | MIT | Data-heavy workbenches that want one full system; `@mantine/hooks` fits beside any kit |
| **Material UI 9** | Material Design components; MUI X for the data grid, charts and date pickers | Emotion, with Base UI adoption growing | Emotion; `StyledEngineProvider enableCssLayer` to sit under Tailwind | Theme provider | Core MIT; MUI X Pro and Premium commercial | Teams that want Material, or the X data grid's depth |
| **daisyUI 5** | Component classes as a Tailwind plugin, with themes | CSS only | Tailwind v4 (`@plugin "daisyui"`) | None | MIT | Fast semantic class names; prefix it when mixing |
| **Magic UI** | Animated components through the shadcn registry (`@magicui/…`) | shadcn tokens, Motion | Tailwind | None | MIT | The signature moment on a shadcn base |
| **Animate UI** | Animated components through the shadcn registry (`@animate-ui/…`) | shadcn tokens, Motion | Tailwind | None | MIT with Commons Clause (never resell the components); its releases have been quiet, so check an item builds before relying on it | The same role as Magic UI |
| **Aceternity UI** | Effects and sections through the shadcn registry (`@aceternity/…`) | Motion, Tabler icons | Tailwind | None | Its own: ship it inside products, never redistribute the source | A site's one expressive moment |
| **React Bits** | Animated components and backgrounds (`@react-bits/…`) | Motion, GSAP and three.js for some items | Tailwind or CSS | None | MIT with Commons Clause; GSAP's standard no-charge licence for the GSAP items | Text and background effects on a site |
| **Motion** | The animation engine (`motion/react`, formerly Framer Motion) | — | — | `LazyMotion` keeps the bundle small | MIT | Orchestration, layout animation and gestures; every kit above sits on it or beside it |

**After `shadcn init`** (Tailwind must already be imported in the entry stylesheet, or the CLI
stops): the CLI writes its own look into the entry stylesheet, and three parts of it are the
generic default the design reference exists to replace. Remove the `@fontsource-variable/inter`
import and the `--font-sans: 'Inter Variable'` line from its `@theme inline` block, and set
`--font-sans: var(--font-ui)` there instead; delete its `:root` and `.dark` token blocks (the
theme's shadcn bridge feeds the same names); and change its dark variant to
`@custom-variant dark (&:where([data-theme=dark], [data-theme=dark] *));` so `dark:` utilities
follow the theme attribute the boot script sets. Keep its `@import "shadcn/tailwind.css"`, its
`@theme inline` colour and radius mappings and its `@layer base` rules; import the theme file right
after the Tailwind import. Pick a preset with `-p` (nova, vega, maia, lyra, mira, luma, sera or
rhea) rather than taking the default, and record it.

Icons: one set per app — `lucide-react` with shadcn, HeroUI and Mantine; Tabler with Aceternity;
Material Symbols with MUI. Utilities that fit beside any kit: `@mantine/hooks` (no CSS, no
provider), `cmdk` for a command palette, `sonner` for toasts, `react-resizable-panels`,
`@tanstack/react-virtual`. Not `vaul`: its repository says it is unmaintained; use the base kit's
drawer or sheet.

## Mixing kits

One base kit owns the global layer: the reset, the design tokens, the theme toggle, the fonts and
any provider. A second kit joins for the components it does better — Mantine's table and date
pickers in a shadcn app, MUI X's grid in a HeroUI app, daisyUI's classes for a prototype area —
under these rules:

1. **Declare the layer order once**, in the entry stylesheet before any import:
   `@layer theme, base, mantine, mui, components, utilities;` with the names you do not use
   dropped. Import Mantine's `styles.layer.css`, never its unlayered `styles.css`; turn on MUI's
   `enableCssLayer`; keep Tailwind's utilities last so a utility wins wherever you reach for one.
2. **Bridge the tokens.** The theme file is the source: shadcn reads its bridge block; Mantine's
   `createTheme` and MUI's `createTheme` take the brand and surface colours, the radius and the font
   families as `var(--…)` values from the same custom properties. One palette, one radius, one font
   stack, whichever kit renders a component.
3. **One of each primitive.** One dialog system, one tooltip system, one toast, one icon set, one
   date library, one portal root with `isolation: isolate`. Two focus-trap implementations fighting
   over one dialog is the mixing bug users report first.
4. **Prefix the class-based kit** when two kits generate classes: daisyUI's `prefix: "d-"`, or
   shadcn's `tailwind.prefix`.
5. **Measure the bundle** after the second kit lands and put the number in the packet. A second
   kit for one component is usually the wrong trade, and the packet says so when it is.
6. **The collections belong with shadcn.** Magic UI, Animate UI, Aceternity UI and React Bits
   install through the shadcn registry and expect shadcn's `cn` helper and token names. In an app on
   another base kit, add the theme's shadcn bridge block and the `cn` helper, then install the item
   into its own folder.

## Data, routing and forms

| Need | Reach for | Notes |
|---|---|---|
| Server state | **TanStack Query 5** | `queryOptions` per endpoint; `useSuspenseQuery` inside a boundary; the query layer owns retries |
| Typed API client | **openapi-typescript** with **openapi-fetch** and **openapi-react-query** | Generated from the service's OpenAPI document ([API reference](./api.md)); `@hey-api/openapi-ts` with its TanStack plugin when generated query options are wanted |
| Routing in a new app | **TanStack Router** with `@tanstack/router-plugin`: file-based, typed search params validated by a Zod 4 schema | An existing app keeps React Router, and a feature change never migrates one to the other; `nuqs` gives a React Router app typed URL state |
| Tables | **TanStack Table 9** (`useTable`, features imported explicitly) with **TanStack Virtual** | AG Grid Community (MIT) for spreadsheet-grade editing; Perspective for streaming grids past about 100k rows |
| Forms | **react-hook-form** with `@hookform/resolvers` and a **Zod 4** schema, or **TanStack Form** | Standard Schema either way; server problems land through the problem helper |
| Dates | **date-fns 4** with `@date-fns/tz` | Temporal is not in every stable browser yet; `Intl.DurationFormat` is |
| Charts | **Recharts 3** for ordinary charts; **uPlot** for streaming series; **ECharts 6** for large or unusual datasets; **visx** for a bespoke one-off; `@mantine/charts` on a Mantine base | Every chart reads the theme tokens and has a table alternative |
| Editors and viewers | CodeMirror 6 through `@uiw/react-codemirror` for in-app query editors; Monaco only for VS Code parity; `react-markdown` with `rehype-sanitize`; `shiki`; `@xterm/xterm` 6; `@xyflow/react` for graphs | Monaco and xterm are heavy: lazy-load them |
| Live data | The `eventsource` package (fetch-based, so it carries headers) or native `EventSource` for cookie sessions; a WebSocket only when the browser must send | Events land in the query cache; `BroadcastChannel` and Web Locks let one tab own the connection |
| Keys and palette | `cmdk`, `react-hotkeys-hook` | Shortcuts act only in their region, never inside inputs, never destructively |

## Platform features to use

Baseline widely available: container queries, `oklch()`, `color-mix()`, `<dialog>`, CSS nesting,
`BroadcastChannel`, Web Locks. Newly available and fine for the team's evergreen browsers:
`light-dark()` (the theme depends on it), the `popover` attribute, `@starting-style`,
`transition-behavior`, same-document view transitions, `content-visibility`, anchor positioning
(keep a JS fallback for menus that must flip), `field-sizing: content`. Still limited: scroll-driven
animations and Temporal. React 19.3 ships `<ViewTransition>`, `<Activity>`, `useEffectEvent`,
`use()` and the Actions hooks as stable.

## Vue

Allowed, not the focus: an existing Vue app keeps Vue, and a new app is Vue when the caller or the
neighbouring apps say so. The equivalents are in the [Vue reference](./vue.md).
