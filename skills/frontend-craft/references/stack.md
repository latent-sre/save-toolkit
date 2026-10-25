# Stack: toolchain, kits and libraries

Preserve repository choices; verify compatibility and licences for added capabilities.

## React toolchain

- **React 19.3, Vite 8 and strict TypeScript.** Scaffold with
  `npm create vite@latest -- --template react-ts`. Node 22.12+ (24 LTS); npm with one committed
  lockfile (keep pnpm where already used).
- **TypeScript 6** (`<6.1.0`) while `typescript-eslint` requires the classic compiler API absent
  from native TypeScript 7 (`@typescript/native`). Run `tsc --noEmit` for typechecking. Use
  `"paths": { "@/*": ["./src/*"] }` without `baseUrl` (deprecated in TypeScript 6 (`TS5101`) and
  removed in TypeScript 7), mirrored by Vite's `resolve.alias`.
- **React Compiler:** `babel({ presets: [reactCompilerPreset()] })` beside `react()`
  (`@vitejs/plugin-react`, `@rolldown/plugin-babel`, `@babel/core`,
  `babel-plugin-react-compiler`) plus `eslint-plugin-react-hooks` recommended rules; or experimental
  `react({ compiler: { reportDiagnostics: true } })` with `oxc-transform-react` (`>=0.152`;
  `compiler.logDiagnostics` is deprecated in `@vitejs/plugin-react` 6.1.2+).
- **Tailwind v4:** `@tailwindcss/vite`; `@import` [theme.css](../assets/theme.css) in the Tailwind
  stylesheet right after `@import "tailwindcss"`.
- **Lint and tests:** ESLint 10 flat config with `typescript-eslint` type-checked promise rules,
  React hooks/refresh plugins and Prettier (or repo-standard oxlint / Biome 2). Vitest 5, Testing
  Library, MSW 3, jsdom (or Vitest browser mode for layout) and `vitest-axe`.

For Vue apps, use [Vue](./vue.md).

## Component kits

Approved kits may start or join an app. One base kit owns reset/tokens/providers; additions follow
the mixing rules, not a one-kit limit.

| Kit | Fit and integration | Licence |
|---|---|---|
| **shadcn/ui** | Default base: CLI source (`shadcn`), Tailwind v4 + CSS tokens; Base UI default, Radix (`-b radix`) or React Aria (`-b aria`); no provider | MIT |
| **Radix UI** | Unstyled `radix-ui` primitives; Radix Themes adds CSS and `<Theme>` | MIT |
| **Base UI** | Unstyled `@base-ui/react` primitives; no provider; isolate app root (`isolation: isolate`) | MIT |
| **HeroUI v3** | Styled React Aria kit; Tailwind v4, `@heroui/styles` after Tailwind; no provider | MIT |
| **Mantine 9** | Workbench suite: components, hooks, forms, dates, charts, notifications; `MantineProvider` and `styles.layer.css` | MIT |
| **Material UI 9** | Material Design + MUI X data-grid; theme provider, Emotion and `StyledEngineProvider enableCssLayer` | Core MIT; X Pro/Premium commercial |
| **daisyUI 5** | Tailwind `@plugin "daisyui"`; no provider; prefix (`prefix: "d-"`) when mixing | MIT |
| **Magic UI** | Animated shadcn registry items (`@magicui/…`), Tailwind and Motion | MIT |
| **Animate UI** | Animated shadcn registry items (`@animate-ui/…`), Tailwind and Motion | MIT with Commons Clause (no resale) |
| **Aceternity UI** | Effects/sections (`@aceternity/…`), Tailwind, Motion and Tabler icons | Custom (product use allowed, no source redistribution) |
| **React Bits** | Text/background effects (`@react-bits/…`), CSS/Tailwind, Motion/GSAP/three.js | MIT with Commons Clause (+ GSAP standard licence) |
| **Motion** | Animation engine `motion/react`; `LazyMotion` limits bundle size | MIT |

After `shadcn init` (`-p` selects a named or `shadcn/create` preset), align the font import with
`--font-sans: var(--font-ui)`,
replace generated `:root`/`.dark` blocks with the [theme bridge](../assets/theme.css), and set
`@custom-variant dark (&:where([data-theme=dark], [data-theme=dark] *));`.

Use one icon set (Lucide, Tabler or Material Symbols). Prefer base-kit drawers over unmaintained
`vaul`.

## Mixing kits

1. **One global owner:** declare CSS layers once before imports
   (`@layer theme, base, mantine, mui, components, utilities;`, dropping unused names); use
   Mantine `styles.layer.css` and MUI `enableCssLayer` so `utilities` stays last.
2. **Bridge tokens:** map [theme.css](../assets/theme.css) into shadcn's bridge and additional
   kit providers, including colours, radius and fonts.
3. **One interaction system per primitive:** keep a single owner for dialogs/modals, tooltips,
   toasts, icons and dates across the app to avoid competing focus traps and portal roots.
4. **Avoid collisions:** prefix daisyUI/Tailwind where needed; weigh bundle/provider cost against
   the existing kit.
5. **Bridge animated collections:** provide `cn` and shadcn token variables when mounting
   shadcn-registry animations on another base kit.

## Data, routing and forms

| Need | Default and alternatives |
|---|---|
| Server state | **TanStack Query 5**, endpoint `queryOptions`; query layer owns retries |
| Typed API | **openapi-typescript**, **openapi-fetch**, **openapi-react-query**; **@hey-api/openapi-ts** (with TanStack plugin); see [API](./api.md) |
| Routing | **TanStack Router** (`@tanstack/router-plugin` + Zod 4 search validation) for new apps; keep **React Router** (`nuqs` for typed URL state) in existing apps |
| Tables | **TanStack Table 9** (`tableFeatures({...})` + `useTable`, keeping `features`, `columns` and empty-array fallbacks outside render or memoized; `useReactTable` is removed) and **TanStack Virtual**; **AG Grid Community** (MIT); **Perspective** |
| Forms & dates | **react-hook-form** + **@hookform/resolvers** + **Zod 4**, or **TanStack Form**; **date-fns 4** + **@date-fns/tz** |
| Charts | **Recharts 3**, **uPlot** (streams), **ECharts 6**, **visx**, **@mantine/charts** |
| Editors/viewers | **CodeMirror 6** (`@uiw/react-codemirror`), **Monaco** (lazy-load), **react-markdown** + **rehype-sanitize**, **shiki**, **@xterm/xterm 6** (lazy-load), **@xyflow/react** |
| Keyboard | **cmdk**, **react-hotkeys-hook** (region-scoped, inactive in inputs, never destructive) |
