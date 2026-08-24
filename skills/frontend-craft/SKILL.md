---
name: frontend-craft
description: >-
  Build or change a web UI — pages, dashboards-as-app-features, forms, admin panels — from a single
  page to a full SPA, including serving it on PCF. Owns UI-layer TypeScript/React idiom — component
  state, interaction, accessibility, resilience UX. Triggers: 'build a UI for', 'add a
  page/form/table', 'make this dashboard page'. Ownership map only—not a load: backend-craft owns
  the service behind the UI, obs-dashboards owns Grafana operations dashboards, and language-idiom
  owns the universal TypeScript language rules loaded alongside this skill.
argument-hint: "[the UI to build or change]"
---

# Frontend craft

**You write the actual code.** Complete, runnable files — components, styles, config, wiring — never pseudo-code, never "you could use X," never TODO stubs. If a decision is needed, make it, state it in one line, and build. Exception — a material fork (the answer changes what gets built: data model, auth, interface scope) that can't be inferred is worth one batched question round with recommended defaults *before* building; a wrong build costs a full rebuild-and-review cycle, a question costs seconds. If the *requested* approach has a materially better alternative, recommend it in one line with the trade-off — then build what was chosen; never silently substitute your own preference.

This skill is general-purpose — any web UI, not just operator tooling — held to an SRE-grade bar: failure-first, verifiable, operable. The examples lean ops-flavored; the rules are domain-neutral and apply to a SaaS product or a hobby project the same way.

## Layout — organized, uncluttered, space-efficient

- **App shell — default to a sidebar rail.** Any app with more than ~5 destinations gets a persistent left sidebar rail, not top tabs (tabs don't scale past a handful and this is the preferred shell): icon + label nav grouped by area, the active item marked with an accent bar or tint, a brand mark at the top and the user/account with theme toggle pinned at the bottom. Top tabs or a single-column layout are reserved for genuinely small apps (≤5 views) or a focused single-purpose tool. The rail collapses to icons-only on narrow viewports.
- **Hierarchy first**: one primary action per view; group related controls; the eye should land on what matters without hunting.
- **Spacing grid**: consistent scale (4/8px steps), generous whitespace at decision points, higher density where data lives — tables and lists earn compactness, forms and actions earn air.
- **Constrain line lengths**: max content width; multi-column only when content genuinely parallels.
- **Stable under state change**: reserve space for the longest content a slot can hold — labels, counts, badges, hover affordances — so interaction and data updates never shift neighboring layout; verify text fit at narrow widths (long labels wrap or truncate by design, never overflow).
- **Typography**: 4–5 sizes total; hierarchy through size and weight, never color alone.
- **Color & theme**: all color through theme tokens, both themes from day one. Ship a manual light/dark/system toggle, persisted and defaulting to the OS setting — and set the theme class in an inline `<head>` script *before first paint* so there's no flash of the wrong theme on load. The palette itself lives in Visual character below.

## Visual character — designed, not default

Organized and uncluttered is the floor, not the ceiling. The bar: at home next to Linear or Vercel's dashboard with the color courage turned up — never mistakable for an unstyled admin template.

- **Dark-first, layered surfaces.** Dark is the designed-for theme (light stays supported via tokens): a deep page background, cards a distinct step lighter, raised elements a step lighter again. Depth comes from this layering plus low-alpha borders and soft shadows — not heavy lines.
- **Color with courage.** One vivid accent used confidently: gradient touches on primary actions and active states, and one hero moment per view — a gradient heading, a glowing stat. Status colors saturated enough to glow against dark surfaces; status pills get a colored dot *plus* text, never color alone.
- **Categorical accents on KPI grids.** When a view shows a row of distinct metrics or stat cards, give each its own accent hue (e.g. purple / teal / amber / cyan) rather than repeating one color — the color *codes* the category, with the icon and number tinted to match. Elevate one card above the rest (an accent border-glow on the most important metric) so the grid has a focal point. Keep the accent set to ~4–5 hues drawn from the theme tokens; this is categorical coding, not a rainbow.
- **Typography with character.** A quality UI font (Inter or similar, self-hosted — no CDN dependency), tight letter-spacing on large headings, `tabular-nums` for data, big confident numbers on stat tiles.
- **Depth cues, spent sparingly.** Rounded-xl cards, soft elevation shadows, hover lift (small translate + shadow), accent-colored focus rings. If every surface is elevated, nothing is.
- **Designed states.** Skeleton shimmer instead of spinners for content areas; empty states get an icon and a call to action; icons anchor navigation, actions, and stats.
- **Every view is a composition.** If the primary content fills only a fraction of the viewport, that's a design defect: either enrich the view (supporting detail, recent activity, a trend over time — whatever the data honestly supports) or constrain the canvas to fit the content. Never ship a screen that is mostly empty page.

**Self-critique as you build** — screenshot what you made and look at it: would a stranger read it as a templated default? Generated UIs cluster around a few stock looks (cream page + serif display + terracotta accent; near-black + one acid accent; hairline-rule broadsheet) and stock component tells (uniform rounded-2xl, purple-to-indigo gradients as the default aesthetic, a shadow on every surface) — a look you fell into is not a decision you made; change one real thing. Spend your boldness in one place: one deliberate risk you can justify, everything around it quiet. Branded or bespoke work sources its distinctive choices from the subject's own world — its materials, instruments, vernacular — never a house style carried from the last project.

## Motion — smooth, purposeful, alive

- Transitions 150–250 ms, ease-out; animate `opacity` and `transform` only (compositor-friendly — no layout thrash).
- Micro-interactions are part of the design, not decoration on top of it: hover lifts, pressed states, animated number changes on live stats, staggered list entrances (30–50 ms steps), smooth expand/collapse.
- Motion serves state change and perceived quality — but stays fast and interruptible; if an animation makes the user wait, cut it.
- Respect `prefers-reduced-motion`.

## State and data

- **React branch only:** never import `@mantine/core` or any styled Mantine component — its CSS reset fights Tailwind's, and that mix is the one incoherent hybrid. Mantine's *hooks* and `@mantine/form` ship no CSS and can mix in React; its *components* do not.
- Server state lives in TanStack Query (caching, retries, invalidation); UI state stays local. No global store until two distant components genuinely share state.
- **Typed API client derived from the contract** — use the OpenAPI spec or shared types as the source of truth, with `openapi-typescript`/`orval`; generate against the versioned server contract and fail CI on incompatible schema drift. Regenerate on contract change and let `tsc` catch the breaks; never hand-maintain response shapes in two places.
- Every async view has designed **loading, error, and empty states**. The empty state is a real design ("no targets configured yet — add one") — never a blank region.
- **Live data**: prefer **SSE** (`EventSource`) for one-way server→client streams (status, metrics, logs) — simpler than WebSocket and it auto-reconnects; use WebSocket only when the client must push too. Feed updates into the Query cache so streamed and fetched data share one source of truth; fall back to interval polling when no stream exists.

## Routing & URL state

- **TanStack Router** for the SPA: typed routes, nested layouts under the app shell, route-based code splitting so each view lazy-loads.
- **The URL is state.** Search text, active filters, page, sort, and the open tab/detail live in URL search params — the back button works, links are shareable, a refresh restores the view. Never keep that state only in component memory.

## Resilience UX — failure-first, for any app

The SRE lens is just good engineering pointed at the screen: assume every call can fail or hang, and design that path first. True for a SaaS app or a hobby project as much as an ops console.

- **Error boundaries per panel**: a view is many independent widgets; one failing query shows a small inline error in *its* card, never a white screen for the page.
- Errors say what happened *and* what to do next; raw stack traces never reach the user.
- Buttons disable while pending (no double-submits); no infinite spinners — every wait times out into an actionable error state.
- Optimistic updates only with visible rollback on failure.
- **Toasts** confirm actions (saved / deleted / failed) and carry the retry for a failed background action; they never replace inline validation.

## Interface copy — words are design material

- Words exist to make the UI easier to understand and use, never to decorate — same intent as spacing and color. Write from the user's side of the screen: name things by what people control and recognize, never by system architecture ("Notifications," not "webhook config"). Specific beats clever.
- A control says exactly what happens when used ("Save changes," not "Submit"), and an action keeps one name through its whole flow — the button that says **Publish** produces the toast that says **Published**. One term per concept everywhere; consistent vocabulary is how people learn the product.
- **Real content only** — never lorem or placeholder filler. If the content doesn't exist yet, writing it is part of the job.
- The *mechanics* of loading/error/empty states live in Resilience UX above; their *wording* lives in [interface copy](./references/ux-writing.md), per the table below.

## Accessibility (baseline, not optional)

Semantic HTML first; every input labeled; keyboard reachable with visible focus; contrast at AA. If a div has an onClick, it wanted to be a button. On route change, move focus to the main heading and scroll to top — SPA navigation is silent to a screen reader otherwise. Responsive by default: the sidebar collapses to a drawer on narrow viewports, touch targets are ≥44px, and data tables reflow or scroll rather than overflow the page.

## Performance

- Route-based code splitting (lazy-load each view) and lazy-load heavy widgets — charts, editors, anything not needed on first paint.
- **Prefetch on intent**: prefetch a route's data (TanStack Query) on hover/focus of its link, so navigation feels instant.
- Fetch in parallel, never in a waterfall; let TanStack Query dedupe. Watch bundle size — a dashboard shouldn't ship a megabyte of JS to show five numbers.

## Testing & quality gate

- **Vitest + the target repository's established component-testing layer + MSW component/contract tests** — test behavior the user can observe (validation, conditional rendering, error/empty states), not implementation details, and mock the API at the network layer. For the React greenfield stack, use React Testing Library; a Vue target keeps its established Vue component-testing layer. Write the failing regression first.
- **Playwright critical-path test** for each end-to-end flow whose breakage would page someone. Write the failing regression first, then prove the fixed path in a real browser.
- Before "done": it typechecks, lints, unit + E2E tests pass, the dev server runs, and the primary flow was exercised in a **real browser render**, including a keyboard-only pass — evidence in the review packet. A UI that compiles but was never rendered is written, not verified.

## Before you write it — load the reference for what you're building

Everything above applies to every UI task. The rules below apply only when the view involves the thing
named. Read the file **before** writing that code, not after — and name what you read in your review
packet.

| If the view involves… | Read first |
|---|---|
| a greenfield/unbranded visual language | [design language](./references/design-language.md) |
| dialogs, drawers, menus, tabs, custom widgets, or async announcements | [interaction accessibility](./references/interaction-a11y.md) |
| labels, actions, errors, empty states, or toasts | [interface copy](./references/ux-writing.md) |
| choosing a stack for a greenfield UI | Load `stack-profile` first, then [stack](./references/stack.md) |
| a table, list, or grid of records | [data views](./references/data-views.md) |
| a chart, graph, or metric visualization | [data visualization](./references/data-viz.md) |
| a form or any user input to submit | [forms](./references/forms.md) |
| login, tokens, or route guarding | [auth](./references/auth.md) |
| React UI code — the request names React, touched code imports React, the target UI package declares `react`/`react-dom`, or the greenfield stack selected React | [React](./references/react.md) |
| Vue UI code — the request names Vue, the target is a Vue `.vue` SFC or Vue composable, or touched code imports from `vue` | [Vue](./references/vue.md) |

"Component," "SPA," JSX, or a `.tsx` suffix is not framework evidence. Preact, Solid, and other JSX
runtimes are not React. If neither the request nor the target UI package/touched code identifies
React or Vue, read neither framework reference.

Trips two predicates? Read both. Trips none? The core above is the whole job.
