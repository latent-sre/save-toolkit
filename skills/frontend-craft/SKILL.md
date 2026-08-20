---
name: frontend-craft
description: >-
  Build or change product web UI: pages, forms, tables, admin panels, client-side state, interaction,
  accessibility, and resilience UX in the repository's existing framework. Use for browser-facing
  application features and product charts. Not for the backend API, Grafana operations dashboards,
  or language-only review; those belong to backend-craft, obs-dashboards, and language-idiom.
  Triggers: 'build a UI', 'add a form', 'change this product page'.
argument-hint: "[the product UI to build or change]"
---

> **Evidence default — `[unverified]`.** Unless a paragraph carries a narrower label, each
> stack/product-specific command, query, API or CLI behavior, version, licensing statement, and
> runtime claim in this skill and its bundled files is `[unverified]` for the exact target.
> A narrower `[sourced]` or `[verified]` label takes precedence; handoffs never upgrade it.

# Frontend craft

Build the runnable UI change: components, styles, state, integration, and tests. Inspect the
repository first and preserve its framework, router, design system, testing tools, and deployment
shape. Before recommending a runtime, library, or infrastructure change, load `stack-profile`.
Ask only when a material product or authority decision cannot be inferred; otherwise state the
decision briefly and implement it.

## Product boundary and design

- This lane owns product UI, including charts embedded in the application. Grafana and other
  operations dashboards stay with `obs-dashboards`; do not rebuild them as product pages.
- Start from the user task and existing information architecture. Make hierarchy, the primary
  action, navigation, and responsive behavior clear. Do not impose a sidebar, dark theme, animation
  style, component library, or framework merely because it is a preferred example.
- Use the existing brand/design tokens. For greenfield work, record audience, workflow density,
  layout, type, color/status semantics, and one product-specific visual decision before styling.
- Keep layout stable under loading, localization, long labels, validation, and live updates. Color is
  never the only carrier of status or action.

## State, data, and URLs

- Derive API types from the server contract or the repository's established shared types. Treat all
  responses as untrusted at the boundary; never hand-maintain competing public shapes.
- Keep server/cache state, durable navigation state, and ephemeral interaction state separate using
  the repository's established tools. Add a router, cache, table, or global-state library only when
  the capability is needed.
- Put queries, filters, sort, pagination, selected tabs/resources, and other durable navigation state
  in validated path/search state when refresh, back/forward, bookmarking, or sharing must restore it.
  Keep secrets, large payloads, and transient UI state out of URLs.
- Every async surface has explicit loading, error, empty, and success behavior. Preserve useful
  content when one panel fails; errors state what happened and the next safe action.
- Pending actions prevent duplicate submission. Optimistic changes need visible failure recovery;
  a toast may confirm an outcome but never replace inline validation or persistent error state.

### Live data

Use polling, SSE, or WebSocket according to the interaction—not a house default. Native browser
`EventSource` cannot attach an `Authorization` header; use an approved same-origin cookie session or
a short-lived, read-only, stream-specific credential, never the primary token in the URL. Define
event IDs/resume, duplicate replay, bounded reconnect, terminal auth failure, logout/unmount cleanup,
slow-consumer behavior, and a polling fallback where required.

## Interaction and accessibility

- Prefer semantic HTML and established accessible primitives. Every control has an accessible name;
  forms programmatically associate labels, errors, requirements, and help with their fields.
- All behavior is keyboard reachable with visible focus. Overlays move focus in and restore it;
  custom widgets implement their complete keyboard and ARIA state model. Announce asynchronous
  status without replacing content unnecessarily.
- Meet WCAG 2.2 AA: normal text contrast 4.5:1, large text 3:1, and applicable non-text boundaries/
  states 3:1. Focus must remain visible and not be entirely obscured. The AA target-size minimum is
  24×24 CSS pixels with defined exceptions; 44×44 may be a stricter project/touch preference, not an
  AA claim.
- Respect reduced motion. Animation must explain state change, remain interruptible, and never delay
  task completion.

## Performance and failure behavior

- Avoid request waterfalls; cancel or ignore stale work and bound polling/reconnect. Code-split or
  virtualize where measured size/render cost or data volume justifies it—do not cargo-cult thresholds.
- Reserve space for expected state changes and prevent layout shifts. Large tables/charts need a
  bounded data window, clear units, and a text or table alternative where the visual is not enough.
- Authentication and authorization remain server-enforced. The UI may guide or hide, but it must
  handle `401`/`403` and never present route guards as a security boundary.

## Verification

- Match the repository's component and browser-test stack. Test observable behavior, not component
  internals: validation, keyboard/focus, loading/error/empty states, stale requests, duplicate
  submission, auth failure, and recovery.
- Run typecheck, lint, component/integration tests, and critical browser flows. Render at narrow and
  wide sizes, use keyboard-only interaction, and run the repository's accessibility checks.
- Inspect the actual UI rather than inferring appearance from code. Record commands, results,
  screenshots or bounded evidence, and any untested browser/assistive-technology gap.

## Load only the reference the task needs

| Task | Reference |
|---|---|
| greenfield or unbranded visual language | [design language](./references/design-language.md) |
| dialogs, menus, tabs, custom widgets, async announcements | [interaction accessibility](./references/interaction-a11y.md) |
| labels, actions, errors, empty states, toasts | [interface copy](./references/ux-writing.md) |
| greenfield stack choice after `stack-profile` | [stack selection](./references/stack.md) |
| table, list, or record grid | [data views](./references/data-views.md) |
| chart, graph, or metric visualization | [data visualization](./references/data-viz.md) |
| form or submitted user input | [forms](./references/forms.md) |
| login, tokens, session, or route guarding | [client auth](./references/auth.md) |
| verified React code/package | [React](./references/react.md) |
| verified Vue code/package | [Vue](./references/vue.md) |

Framework evidence is the request, imports/package manifest, or touched source—not a `.tsx` suffix or
the word “component.” Load every row that applies and no unrelated reference.
