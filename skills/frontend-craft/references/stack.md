# Stack: toolchain, kits and libraries

Choose for the app's job and reuse repository conventions. This is a menu, with recommended
defaults; select only capabilities the app needs. Check registry versions and compatibility
before pinning, and record additions and licences in the handoff.

## Contents

- [React toolchain](#react-toolchain)
- [Component kits](#component-kits)
- [Mixing kits](#mixing-kits)
- [Data, routing and forms](#data-routing-and-forms)
- [Platform features](#platform-features)

## React toolchain

- **React 19.3, Vite 8 and strict TypeScript.** Scaffold with
  `npm create vite@latest -- --template react-ts`; adapt the starting Vite configuration.
  Narrow `unknown` at boundaries; use branded IDs and exhaustive unions where they prevent
  mistakes. Node 22.12 or later, preferably the active LTS line (24). Use npm with one committed
  lockfile; keep pnpm where the repository already uses it.
- **TypeScript 6** while typescript-eslint and vue-tsc require the compiler API absent from
  TypeScript 7. Verify that compatibility before changing the pin. Vite strips types;
  `tsc --noEmit` checks them. Use `"paths": { "@/*": ["./src/*"] }` without deprecated
  `baseUrl`, mirrored by Vite's `resolve.alias`.
- **React Compiler:** `react({ compiler: true })` with `oxc-transform-react` and the
  `eslint-plugin-react-hooks` recommended rules.
- **Tailwind v4:** `@tailwindcss/vite`; the theme's `@theme inline` exposes token utilities once
  the theme is `@import`ed in the Tailwind stylesheet.
  Respect the chosen kit's styling integration below.
- **Lint and format:** ESLint 10 flat config, typescript-eslint's type-checked promise rules,
  React hooks/refresh plugins and Prettier. Keep create-vite's fast oxlint check if useful;
  repository-standard type-aware oxlint or Biome 2 are alternatives.
- **Tests:** Vitest 5, Testing Library, MSW 3 and jsdom. Layout-sensitive components can use
  Vitest browser mode; critical journeys use the host's Playwright MCP server as described in
  the parent skill. Use `vitest-axe` for component accessibility. Adapt asset tests to this runner.

For a Vue app, use the [Vue equivalents](./vue.md).

## Component kits

Any approved kit may start an app or join one. Choose one base kit; additional kits earn their
place through a needed capability and the mixing rules.

| Kit | Fit and integration | Licence |
|---|---|---|
| **shadcn/ui** | Default base: copied source via CLI/registries, Tailwind v4 and CSS tokens; Base UI by default, Radix (`-b radix`) or React Aria (`-b aria`) selectable; no provider | MIT |
| **Radix UI** | Unstyled `radix-ui` primitives; Radix Themes adds a complete look, CSS and `<Theme>` | MIT |
| **Base UI** | Unstyled `@base-ui/react` primitives; no provider; isolate the app root | MIT |
| **HeroUI v3** | Complete styled React Aria kit; Tailwind v4, `@heroui/styles` after Tailwind; no provider | MIT |
| **Mantine 9** | Full workbench system: components, hooks, forms, dates, charts, notifications; `MantineProvider` and layered CSS | MIT |
| **Material UI 9** | Material Design and MUI X data-grid depth; theme provider, Emotion and `StyledEngineProvider enableCssLayer` | Core MIT; X Pro/Premium commercial |
| **daisyUI 5** | Semantic component classes/themes through Tailwind's `@plugin "daisyui"`; no provider; prefix when mixing | MIT |
| **Magic UI** | Animated shadcn registry items (`@magicui/…`), Tailwind and Motion | MIT |
| **Animate UI** | Animated shadcn registry items (`@animate-ui/…`), Tailwind and Motion; check an item builds before relying on it | MIT with Commons Clause; no component resale |
| **Aceternity UI** | Effects/sections (`@aceternity/…`), Tailwind, Motion and Tabler icons | Own licence: use inside products, no source redistribution |
| **React Bits** | Text/background effects (`@react-bits/…`), CSS or Tailwind; some use Motion, GSAP or three.js | MIT with Commons Clause; GSAP items also use its standard no-charge licence |
| **Motion** | Animation engine `motion/react`; orchestration, layout and gestures; `LazyMotion` limits bundle cost | MIT |

After `shadcn init`, reconcile its stylesheet with the brief and theme: align the generated
font import with the chosen face and `--font-sans: var(--font-ui)`; replace its
`:root`/`.dark` tokens with the theme's bridge; use
`@custom-variant dark (&:where([data-theme=dark], [data-theme=dark] *));`.
Keep `shadcn/tailwind.css`, colour/radius mappings and base rules. Tailwind must be imported
before the CLI runs; import the theme immediately after Tailwind. Select and record a fitting
`-p` preset (nova, vega, maia, lyra, mira, luma, sera or rhea).

Use one icon set: Lucide, Tabler or Material Symbols according to the chosen kit and brief.
Useful additions include provider-free `@mantine/hooks`, `cmdk`, `sonner`,
`react-resizable-panels` and TanStack Virtual. Use the base kit's drawer/sheet instead of
unmaintained `vaul`.

## Mixing kits

1. **One global owner:** reset, tokens, theme toggle, fonts and provider. Declare layers once,
   before imports: `@layer theme, base, mantine, mui, components, utilities;`, dropping unused
   names. Use Mantine `styles.layer.css` and MUI `enableCssLayer`; keep utilities last.
2. **Bridge tokens:** feed the theme's brand/surface colours, radius and fonts to shadcn's CSS
   bridge and each kit's theme API. Components share the app identity, including portal content.
3. **One interaction system per primitive:** dialog, tooltip, toast, icon set and date library;
   share an isolated portal root. Avoid competing focus traps.
4. **Avoid class collisions:** prefix daisyUI (`prefix: "d-"`) or shadcn (`tailwind.prefix`)
   when needed.
5. **Measure cost:** report the bundle change after adding a kit and judge it against the
   capability gained.
6. **Bridge animated collections:** their shadcn registry items expect `cn` and shadcn token
   names; supply those on another base kit and keep imported items in their own folder.

## Data, routing and forms

| Need | Default and alternatives |
|---|---|
| Server state | **TanStack Query 5**, endpoint `queryOptions`; query layer owns retries |
| Typed API | **openapi-typescript**, **openapi-fetch**, **openapi-react-query**; **@hey-api/openapi-ts** with its TanStack plugin for generated query options; see [API](./api.md) |
| Routing | **TanStack Router** with `@tanstack/router-plugin` and Zod 4 search validation for a new app; an existing app keeps React Router (with `nuqs` for typed URL state), and a feature change never migrates one router to the other |
| Tables | **TanStack Table 9** (`useTable`, explicit features) and **TanStack Virtual**; **AG Grid Community** (MIT) for spreadsheet editing; **Perspective** for large streaming grids |
| Forms | **react-hook-form**, **@hookform/resolvers**, **Zod 4**, or **TanStack Form** with Standard Schema |
| Dates | **date-fns 4** and **@date-fns/tz** |
| Charts | **Recharts 3** for common charts, **uPlot** for streams, **ECharts 6** for large/unusual data, **visx** for bespoke charts, **@mantine/charts** on Mantine |
| Editors/viewers | **CodeMirror 6** via `@uiw/react-codemirror`; **Monaco** for VS Code parity; **react-markdown** with **rehype-sanitize**, **shiki**, **@xterm/xterm 6**, **@xyflow/react**; lazy-load Monaco/xterm |
| Live data | Native **EventSource** for cookie sessions; fetch-based **eventsource** for headers; WebSocket for bidirectional traffic; see [API](./api.md#live-data) |
| Keyboard accelerators | **cmdk**, **react-hotkeys-hook**; region-scoped, inactive inside inputs, never destructive |

## Platform features

Evergreen-browser options include container queries, OKLCH, `color-mix()`, native dialog,
CSS nesting, BroadcastChannel and Web Locks. The theme uses `light-dark()`; popover,
`@starting-style`, discrete transitions, same-document view transitions, `content-visibility`,
anchor positioning and `field-sizing` are also available in newer browser baselines. Check the
app's supported browsers; keep a fallback where required, especially for flipping menus.
Scroll-driven animations and Temporal still need compatibility checks. React 19.3 includes
`<ViewTransition>`, `<Activity>`, `useEffectEvent`, `use()` and Actions hooks.
