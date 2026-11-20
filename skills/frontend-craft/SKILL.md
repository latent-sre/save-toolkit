---
name: frontend-craft
description: >-
  Build or change web applications and SRE interfaces in React or Vue, from one page to a
  complete app integrated with its backend. Triggers: 'build a UI for', 'add a page/form/table/console',
  'make this look less generic', 'wire the UI to the API'. Not for backend implementation
  (api-craft) or Grafana dashboard design and operations (grafana).
argument-hint: "[the GUI to build or change]"
---

# Frontend craft

Deliver the caller's requested UI change or application with runnable code, verified required
workflows and the real backend integration they need. Use the caller's requirements and repository
facts first; defaults fill open decisions.

Keep an existing app's framework, kit, router, libraries and locked toolchain. Follow its
conventions. Write a [design brief](./references/design.md) for a new app, a new area, or a
visual change larger than one component; ask one round with recommended defaults only for
consequential unsettled choices. Choose an app identity, density and motion budget that fit the
work, with visible actions and keyboard and screen-reader parity.

## Load for the changed boundary

| Boundary | Guidance |
|---|---|
| Framework and kit | [Stack](./references/stack.md) (React default) or [Vue](./references/vue.md) |
| Backend integration, caching, live data or sessions | [API](./references/api.md) |
| Production serving, route fallback, HTTP caching, runtime config or localhost proxy | [Serving](./references/serving.md) |

Load `stack-profile` before recommending runtime, tooling or infrastructure choices. Use
[starting code](#starting-code) selectively: equivalent app or library facilities satisfy the
contract.

## Build the complete workflows

When the work needs backend integration, get one end-to-end path through the running backend
early. Complete every required workflow and its loading, empty, success, error and stale states.
Use a typed client for the backend's actual contract (generate from OpenAPI when available).
Coordinate backend changes through `api-craft`. Mocks and labelled sample data support development
and tests; any integration they replace remains an explicit gap.

- **Recoverable failures.** Route and independent-panel error boundaries contain failures in place
  without dropping the page heading. Every async path ends in a rendered state. Show an actionable
  error, a copyable request ID, time and zone, and safe retry; report boundary catches and
  unhandled rejections to browser error reporting with request ID and release, without secrets.
- **State ownership.** Put shareable, non-sensitive filters, sort, page and tabs in the URL. Add a
  global store only for state shared by distant components. Choose pagination or virtualization
  from rendered rows, interaction and measured cost.
- **Permissions and actions.** For authenticated apps, show the signed-in identity and role.
  Disable visible but forbidden actions with a reason; hide areas the user can never use.
  Reversible actions offer undo; destructive or bulk actions confirm target, count and environment
  with Cancel focused; irreversible or fleet-wide actions also require typing the target name.
  Preserve input on validation failure and show per-item outcomes, including unknown.
- **Content safety.** Render API, log and user text as text. Rich HTML uses the repository's
  sanitizer or DOMPurify; data-driven links and sources allow only `http:`, `https:` and
  `mailto:`. Mask account/client identifiers and personal data until revealed; keep them out of
  URLs, page titles and telemetry. Show timestamp zones (UTC default) with relative time; format
  numbers through `Intl` and preserve server decimals without floating-point conversion.
- **Accessibility.** Use semantic controls and labelled inputs, visible focus and full keyboard
  access. Kit primitives own focus traps, ARIA state and arrow-key behaviour. Navigation moves
  focus to the main heading; same-view updates preserve it. Announce save, completion and error
  status without stealing focus. Reflow at 320 CSS px; targets are at least 24×24 px (44 for
  touch). Provide AA contrast in both themes, reduced-motion variants and chart text/table
  alternatives. Status always includes text or an icon alongside colour.

## Verify before handing off

Run the repository's required checks. Select typecheck, lint, component tests and a production
build for the changed code. Port helper assertions to the existing runner. The `.test.ts` assets
use `node:test` and must not be copied raw into Vitest. Cover applicable
[API cases](./references/api.md#contract-tests).

Choose browser verification scope from the change:

- **New app:** every required workflow, view and state in light and dark at desktop width and 320 px.
- **Existing app:** affected workflows, views and relevant states in its supported themes and
  viewports. Cover shared components in their consuming workflows and global changes across the app.
  For a changed route, check navigation, direct load, reload and focus on the destination.

Use repository browser tests when they cover that scope, including keyboard, focus, accessible
feedback and axe for affected interactions. Check the console for CSP violations and missing
styles. Exercise changed backend integrations against the running service. Fill browser coverage
gaps with available tools such as host Playwright MCP. With MCP, run same-origin `axe-core` through
`browser_evaluate`; report any unavailable checks. Do not install Playwright packages or
download browsers for MCP verification.

Run the [serving contract](./references/serving.md) for a new app or changes to serving, routing,
runtime configuration or HTTP caching. Report the brief when required, workflows, added
dependencies/licences, verification scope and results, screenshots and any unverified gaps.

## Starting code

Copy and adapt only files needed for selected capabilities; reuse equivalent app facilities.

| Capability | Assets and destination |
|---|---|
| App identity | [theme.css](./assets/theme.css) → `src/styles/theme.css` (`@import` right after `@import "tailwindcss"`, or import once before kit styles) |
| API errors | [problem.ts](./assets/problem.ts) → beside the client; port the assertions from [its test](./assets/problem.test.ts) |
| Idempotency-Key writes | [idempotent-write.ts](./assets/idempotent-write.ts) → beside the client (imports `problem.ts`); port the assertions from [its test](./assets/idempotent-write.test.ts) |
| Runtime configuration | [runtime-config.ts](./assets/runtime-config.ts) → bootstrap; port the assertions from [its test](./assets/runtime-config.test.ts) |
| Served-build checks | [serving-contract.mjs](./assets/serving-contract.mjs) → build configuration |
