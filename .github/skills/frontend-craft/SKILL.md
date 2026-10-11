---
name: frontend-craft
description: >-
  Build or change a web UI in React or Vue for the team's SRE tooling and sites — consoles,
  pages, dashboards-as-app-features, forms, admin panels — from one page to a full SPA, including
  wiring it to the API and serving it on PCF or another platform. Owns the browser side of the
  API contract, the error and action surfaces an operator relies on, runtime configuration,
  accessibility, and modern-frontend capability (live data, dense data, motion, rich editing).
  Triggers: 'build a UI for', 'add a page/form/table/console', 'make this dashboard page', 'wire
  the UI to the API'. Not for the service behind the UI (backend-craft) or Grafana/observability dashboards (obs-dashboards to design, grafana to operate).
argument-hint: "[the UI to build or change]"
---

# Frontend craft

Write complete, runnable UI code: components, styles, configuration, tests and wiring. The
repository's existing framework, design system, libraries and conventions win over every default
here; the owner decisions apply wherever the repository has not already chosen. These are
operator tools: an SRE reads them during an incident, so every surface answers "what happened,
what do I do, where is the evidence".

**Before writing any page or view, load the [design reference](./references/design.md) and write
the design brief — even when nobody asked for a look.** A page with no styling is not finished. An
app with no styling of its own is unbranded. Without a component kit, start it from the
[console theme](./assets/console-theme.css); on a kit (shadcn/ui, HeroUI, Mantine and the like),
set the theme's palette and status colours as the kit's own tokens and keep the kit's reset and
element styles, never loading the theme beside it.

This skill's assets are starting files: read each one and write its contents into the app with
the editor tools. The skill's folder is outside the workspace, so never copy from it with the
shell — a `cp` from there is refused or prompts.

## Owner decisions

| Area | Decision |
|---|---|
| Framework | React and Vue are both supported; an existing app keeps its framework. A new app is React unless the caller or its neighbouring apps say Vue. |
| Component library | One component system per app, with animated collections and Motion layered on top; any kit the caller names is allowed. A new React app starts from shadcn/ui + Tailwind + Motion or HeroUI + Motion — ask the caller which; a new Vue app from shadcn-vue + Tailwind + motion-v. |
| Register | Operator tools get the dense, keyboard-first console register; sites get the expressive one. Name it in the design brief before styling. |
| API | The UI consumes `backend-craft`'s house contract: problem+json with a request ID, cursor pages, `Idempotency-Key` on writes. |

## What every UI does

1. **Consumes the contract.** A typed client generated from the OpenAPI document; problem
   responses parsed with the [problem helper](./assets/problem.ts) and
   [its test](./assets/problem.test.ts), written into the app from this skill; cursor pages;
   writes through the [idempotent-write helper](./assets/idempotent-write.ts)
   ([test](./assets/idempotent-write.test.ts)) — one key per user intent, the contract's `409`
   waited out; never a call to `/health/*`.
2. **Shows errors an operator can act on.** Loading, error and empty states are designed before
   the happy path. Each route and independent panel sits in an error boundary, so one failing
   panel shows its own inline card: title, next step, the request ID (copyable, and linked to
   its logs and trace when runtime configuration provides the URL templates), the time with its
   zone, and a retry only when the request is safe. Every async path ends in a rendered state; a
   handler never re-throws to the page. Errors a boundary catches, and unhandled rejections, reach
   the repository's browser error reporting with the request ID and the release, without
   sensitive values. Status never by colour alone.
3. **Makes writes safe.** Friction matches the blast radius: a reversible action runs at once
   and offers undo; a destructive or bulk action shows the exact target, count and environment in
   a confirm with Cancel focused; an irreversible or fleet-wide one also has the user type the
   target's name. Disable the control while the write is pending; report per-item outcomes,
   including unknown. The server is the validation truth; field errors land beside
   their fields with the user's input intact. Actions follow what the server says the user may
   do: one they can see but not run is disabled with the reason, an area they can never use is
   hidden, the shell shows who is signed in and with what role, and the server stays the
   authority.
4. **Builds once for every environment.** Environment values load at startup from same-origin
   runtime configuration; `import.meta.env` and `VITE_*` hold only values identical everywhere
   and never secrets — the bundle ships to every browser. Every environment shows its name,
   production most distinctly. `index.html` is served with a Content-Security-Policy that forbids
   framing and with `nosniff`. The [serving contract](./assets/serving-contract.mjs), written into
   the repository from this skill, is the acceptance test.
5. **Keeps state where it belongs.** Server state in the query cache, with its age visible; UI
   state local; non-sensitive search, filters, page, sort and tabs in the URL when they should
   survive refresh or be shared; no global store until two distant components genuinely share.
   Tables choose pagination or virtualization from rendered rows, interaction needs and measured
   cost; virtualization does not reduce what is fetched, so a dataset too large to fetch pages or
   filters on the server.
6. **Treats content as data.** API, log and user text render as text, never through `v-html`,
   `dangerouslySetInnerHTML` or `innerHTML`; rich text passes the repository's sanitizer
   (DOMPurify if none); data-driven `href` and `src` allow only `http:`, `https:` and `mailto:`.
   Timestamps show the zone (UTC unless the repository sets another), relative time only beside
   them; numbers format through `Intl`; server decimals such as prices never touch floating point.
   Sensitive values — account and client identifiers, personal data — are masked until the user
   reveals them, because consoles are screen-shared on bridges, and never enter URLs, page titles
   or telemetry.
7. **Is accessible by construction.** Semantic HTML, labelled inputs, keyboard access, visible
   focus; focus moves to the main heading on navigation and stays put on same-view updates;
   saving, completion and error status reach assistive technology without stealing focus; layouts
   reflow at 320 CSS px; motion respects `prefers-reduced-motion`. AA contrast in every theme
   shipped. Every chart has a text or data-table alternative. Widget behaviour — focus traps,
   ARIA state, arrow-key navigation — comes from the component system's primitives, or in an app
   without one from a headless library (Base UI, Radix, React Aria, Reka UI), never hand-rolled.
   Simple controls stay native elements — `<button>`, `<a>`, `<input>` — whichever kit styles them.
8. **Looks designed and uses the modern platform.** Theme tokens, deliberate density and the
   register's look on every page — a basic UI is not the target. The saved theme applies before
   first paint through the project's CSP-compatible mechanism (an inline script allowed by hash or
   nonce, never a weakened CSP), so a page never flashes the wrong theme; charts read the theme
   tokens, so they follow light and dark and the status colours. Charts state units, put time
   on UTC axes, draw missing data as a gap (never a zero), and share one time range across the
   view, kept in the URL. When the feature needs them, not on every page: view transitions for
   navigation and list changes; `<dialog>`, the `popover` attribute and `@starting-style` for
   modals, menus and toasts (anchor positioning is not yet Baseline — keep a JS positioner);
   container queries for panels; `BroadcastChannel` and Web Locks so tabs share one feed and one
   sign-out; virtualization for long lists; a command palette for navigation and actions. The
   framework references name the libraries.
9. **Adds dependencies deliberately.** A maintained, typed library that fits the repository's
   licence and lockfile is ordinary work inside an authorized change; name each addition in the
   review packet. Ask the caller before adding a second UI framework, component system or test
   runner, or a global store.

## Done means

Typecheck and lint clean; component tests for changed behavior, with network mocks for changed
network behavior and the contract cases covered — a `500` renders its request ID, a `422` lands
on its fields, `next_cursor` loads the next page, a retried write reuses its key; the assets'
tests green in the app; the serving contract run against the built app when the build or serving
changed. For a bug, prove the failing regression first. If the repository has Playwright or you
have a browser tool, render the affected view and inspect its screenshot; otherwise rely on
component and accessibility tests, name the missing browser pass as a gap, and never add
Playwright or download browsers without the caller's approval. Check changed interactions by
keyboard and displayed status with assistive technology or the available tooling; check layouts
at 320 px (400% zoom from 1280) — two-dimensional tables may scroll, surrounding controls reflow
([status messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html),
[reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html)). The production build ships
the page's stylesheet; a page that renders in browser defaults is not done. A UI never rendered
is written, not verified.

## Before you write it — load the reference for what you're building

| If the work involves… | Read first |
|---|---|
| a React app, or a new React app | [React](./references/react.md) |
| a Vue app, or a new Vue app | [Vue](./references/vue.md) |
| API requests, caching, pages, writes, error display, test doubles | [API](./references/api.md) |
| authentication, sessions, SSE or WebSocket transport | [Sessions](./references/sessions.md) |
| the build, runtime configuration, or serving the UI | [Serving](./references/serving.md) |
| any new page or view, or a visual change larger than a component | [Design](./references/design.md) |
| live views, paused history, reconnects or linked live selection | [Live data](./references/live-data.md) |
| large tables, linked charts, dependency exploration or bulk selection | [Dense data](./references/dense-data.md) |
| animated transitions, orchestrated effects or moving visualizations | [Motion](./references/motion.md) |

Load every matching row. Before recommending a hosting, runtime or platform change, also load
`stack-profile`.
