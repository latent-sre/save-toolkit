---
name: frontend-craft
description: >-
  Design and build distinctive SRE tools and sites: team sites, incident workspaces, automation
  builders, service catalogs, and application pages. Owns visual direction, advanced interactions,
  frontend library selection, React/Vue UI code, and OpenAPI integration.
  Triggers: 'build our team site', 'design an incident workspace', 'build a visual automation builder',
  'improve our service catalog UI'. Not for backend implementation (backend-craft), live incident
  triage (incident-investigation), or Grafana dashboards (obs-dashboards to design, grafana to operate).
argument-hint: "[the product, UI, or frontend design decision]"
---

# Frontend craft

Build complete, distinctive interfaces for the tools and sites SREs use. Give each product its own
visual identity and interaction model, with shared standards for usability and engineering quality.
Aim for sophisticated, finished products whose composition and behavior reflect their purpose.

Dark-first is preferred. Design primarily for desktop and large screens; decide mobile scope per
product. The audience mixes experience levels: make the main task discoverable and give experienced
users efficient navigation, commands, and data exploration.

## Establish the product, then build

Inspect the current workspace, relevant screens, data contracts, and user instructions. For code
changes or stack decisions, load `stack-profile` and its application-and-data reference for the
team's language tooling and platform boundaries. Frontend technology choices are open; React,
TypeScript, and Vite are a familiar starting point, Vue is welcome, and Mantine is approved.
Use the [stack reference](./references/stack.md) when choosing or combining dependencies.

For a new product or a full redesign:

1. Establish the audience, main jobs, representative content/data, important states, and viewport
   needs. Reuse supplied answers; ask only about gaps that would materially change the design.
2. Develop **two genuinely different design directions** using the same representative screen and
   content. Show differences in composition, typography, density, navigation, and interaction or
   motion. Present visual previews when tooling permits; distinguish a prose proposal from a
   rendered concept. Let the user select a direction before expanding the full product, unless
   they have already selected one or explicitly delegated that choice.
3. Refine the selected direction into a coherent visual system and implement the requested flows,
   styles, configuration, and API wiring. Keep the agreed visual ambition through implementation.

For a scoped change, extend the product's established design and framework. An explicitly requested
rebuild can replace them. Do not restart design discovery for a small fix or an already selected
direction. Consult [design language](./references/design-language.md) for new visual direction or
substantial visual work.

## Choose interactions around the work

Actively consider rich tables, linked charts, dependency graphs, visual workflows, command palettes,
expressive motion, and interactive visuals. Select the capabilities that advance the product's jobs
and finish their behavior; a static imitation of an interactive control is unfinished work.

| Product | Starting questions for composition and interaction |
|---|---|
| Team site | What does the team do, what should readers understand, and where can they reach its knowledge and tools? Use editorial structure and interactive explanations suited to that content. |
| Incident workspace | How do responders connect evidence, events, services, and hypotheses? Link tables, charts, timelines, and dependencies through clear context. Preserve the existing bridge or TLC as the coordination channel. |
| Automation builder | How does someone author, understand, validate, preview, and inspect a workflow? Make connections, step configuration, and execution states understandable. |
| Service catalog | How do users find services, understand ownership and dependencies, and reach the relevant actions? Combine useful table views with substantial service details and relationship exploration. |

Read [advanced interactions](./references/interactions.md) for these capabilities. These are product
patterns to select from, not a requirement to put every capability into every product.

## Engineering quality

- Use semantic theme tokens, WCAG AA contrast in every shipped theme, labelled controls, keyboard
  access, and visible focus. Pair status color with text or an icon. Apply the theme before paint through
  a CSP-compatible mechanism. Respect reduced motion without losing information or functionality.
- Put shareable, non-sensitive filters, sort, pagination, time range, and selected context in the
  URL when appropriate. Keep credentials, sensitive values, and unsaved drafts out of URLs.
- Design loading, empty, validation, error, stale, disconnected, and partial-result states alongside
  the normal workflow. A failing region must leave unaffected work usable. Preserve selection and
  drafts across recoverable refreshes and failures through a storage strategy suitable for their
  sensitivity; do not persist secrets merely to restore a form.
- Separate server/cache state, navigation state, and local interaction state. Use the state model
  the workflow needs; choose freshness, request ownership, and rendering strategy deliberately.
- Integrate Python and Go services through their OpenAPI contracts; FastAPI is the Python backend
  framework. Generate or maintain typed clients against the actual schema and detect contract drift.
  Read [network and sessions](./references/network-and-sessions.md) for requests, forms, sessions,
  actions, and live data. Backend implementation belongs to `backend-craft`.
- For destructive or bulk actions, show the exact target and count, require explicit confirmation,
  prevent duplicate submissions, and show actual per-item outcomes, including unknown outcomes.
  Use the API's idempotency contract when available. A palette or keyboard shortcut follows the same
  authorization and confirmation path as the visible control.
- Use realistic content and data, including long names, dense results, and missing values. Clearly
  distinguish fixture data and simulated execution from connected behavior.

## Verify the product that was built

Use the project's checks for the affected behavior: typecheck, lint, production build, focused
component/integration tests, and browser checks for critical flows. For a bug, demonstrate the
regression. For serving or hosting changes, read [build and serving](./references/serving.md).

Render the affected views with available browser tooling and inspect screenshots against the chosen
direction. Exercise real interactions and failure states, including keyboard paths, focus after
navigation/dialogs, and announcements of saving, completion, and errors. Page navigation should move
focus into the new page; same-view filtering should preserve it. Inspect the intended desktop
and large-screen layouts, reduced-motion behavior, and browser zoom/reflow. At 320 CSS pixels,
surrounding controls and text must remain usable; genuinely two-dimensional tables, graphs, and
canvases may need scrolling or a focused alternative. Product-specific mobile scope does not remove
keyboard or zoom accessibility.

Check linked views for consistent context, graphs and tables with representative data volume, and
motion while work is in progress. Measure interaction cost when scale or animation makes it material.
Revise visual and interaction defects found in the rendered result. Report what was implemented,
what was exercised, and remaining gaps; tests alone do not establish visual quality, and a UI that
was never rendered has no verified visual result.
