---
name: frontend-craft
description: >-
  Build or change a web UI — pages, dashboards-as-app-features, forms, admin panels — from a single
  page to a full SPA, including serving it on PCF. Owns UI-layer TypeScript/React idiom — component
  state, interaction, accessibility, resilience UX. Triggers: 'build a UI for', 'add a
  page/form/table', 'make this dashboard page'. Not for the service behind the UI (backend-craft) or Grafana/observability dashboards (obs-dashboards to design, grafana to operate).
argument-hint: "[the UI to build or change]"
---

# Frontend craft

Write complete, runnable UI code, including styles, configuration and wiring. The product's
existing brand, design system, framework and conventions take precedence over defaults below.

Before any UI code change, load `stack-profile` and its application-and-data reference; read the
TypeScript/JavaScript row under "Toolchain by language".
That table owns language and test-tool defaults; the repository's existing tooling wins.

## Invariants

| Rule | What it means here |
|---|---|
| Color through tokens | All colour through theme tokens; status never by colour alone (a dot plus text or an icon); AA contrast in every theme shipped. |
| Theme without a flash | Apply the persisted theme before first paint using the project's CSP-compatible mechanism; allow an inline script with a matching hash or nonce, without weakening CSP. |
| Shareable URL state | Put appropriate, non-sensitive search, filters, page, sort, tabs, and details in the URL when they should survive refresh or be shared; keep sensitive values and transient drafts out. |
| Failure-first | Loading, error, and empty states are designed before the happy path; one failing panel shows an inline error in its own card. |
| Every view is a composition | Use hierarchy and spacing to serve the workflow; focused tasks and empty states can use deliberate whitespace. |
| Real content | Real copy, never lorem or filler. |
| Accessibility is baseline | Semantic HTML, labelled inputs, keyboard access and visible focus. Move focus to the main heading on page navigation; preserve it during same-view filter/tab updates. Make displayed saving, completion and error status available to assistive technology without stealing focus. |

## Decisions this fleet has made

| Area | Decision |
|---|---|
| Mantine | React targets never import `@mantine/core` or any styled Mantine component — a house styling policy that avoids another styled component system. Mantine can integrate with Tailwind through deliberate CSS setup; this policy is not a compatibility claim. |
| Mantine hooks/form | `@mantine/hooks` and `@mantine/form` are fine in React; never recommended for Vue. |
| State | Server state lives in the query/cache layer (TanStack Query in the greenfield stack); UI state stays local — no global store until two distant components genuinely share state. |
| API client | A typed API client generated from the OpenAPI contract; CI fails on drift. |
| Forms | `react-hook-form` or `@mantine/form` when React form state needs a library; `v-model` plus the repo's validation layer in Vue; the server is the validation truth. |
| State-changing actions | Show the exact target and count before a destructive or bulk action and require an explicit confirm; disable the control while the write is pending; send one `Idempotency-Key` per user intent where the API accepts one, reused on retry; show per-item outcomes (including unknown) for bulk actions. |
| Charts | Recharts v3 by default in React, visx for a bespoke one-off, uPlot for dense real-time series; streamed series batch or throttle redraws per frame and keep a rolling window; never `@mantine/charts`; charts read theme tokens; give every chart a text or data-table alternative. |
| Tables | TanStack Table when needed; choose pagination or virtualization from rendered rows, interaction needs and measured cost. Virtualization does not reduce fetched data; use server-side operations or incremental fetching when the dataset is too large. Keep sort/filter/page shareable in the URL. |
| Auth and sessions | Preserve the project's auth contract. Never put browser bearer tokens in `localStorage` or URLs; cookie-authenticated writes need CSRF protection. Read the conditional network reference below for auth and session mechanics. |
| Live data | SSE for one-way live data via the query cache; close subscriptions on view/session end, show stale/disconnected state, and resynchronize after reconnect gaps. |

## Done means

Use the repository's existing verification tools for the affected capabilities: typecheck and
lint, component/unit tests for changed behavior, network mocks for changed network behavior, and
browser automation for changed critical flows. For a bug, prove the failing regression first.
Run the relevant checks. If the repository already has Playwright or you have a browser tool,
render the affected view and inspect its screenshot; otherwise rely on component and existing
accessibility tests, name the missing browser pass as a gap, and never add Playwright or download
browsers without the caller's approval. Check changed interactions by keyboard and displayed status
with assistive technology or the available accessibility tooling. Check affected layouts at 320 CSS
pixels wide (e.g. 400% zoom from 1280); genuinely two-dimensional tables may scroll, but surrounding
controls must reflow. Scale checks to the change and report gaps. A UI never rendered is written, not verified.
The [status-message](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html) and
[reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html) criteria define these checks.

## Before you write it — load the reference for what you're building

| If the view involves… | Read first |
|---|---|
| a greenfield or unbranded UI — nothing to match | [design language](./references/design-language.md) |
| choosing a stack for a greenfield UI, or serving a SPA on PCF | Load `stack-profile` first, then [stack](./references/stack.md) |
| API requests, query caching, authentication, sessions or live updates | [network and sessions](./references/network-and-sessions.md) |

Load every matching row. The language guidance above applies to every UI code change.
