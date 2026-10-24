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

Deliver a complete application with runnable code, real backend integration and verified user
workflows. Use the caller's requirements and repository facts first; defaults fill open decisions.

In an existing app, keep its framework, kit, router, libraries and conventions; never migrate them
as a side effect. Write a [design brief](./references/design.md) for a new app, a new area, or a
visual change larger than one component; ask one round with recommended defaults only for
consequential unsettled choices. Choose an app identity, density and motion budget that fit the
work, with visible actions and keyboard and screen-reader parity.

## Load for the changed boundary

| Boundary | Guidance |
|---|---|
| Framework and kit | [Stack](./references/stack.md) (React default) or [Vue](./references/vue.md) |
| Backend integration, caching, live data or sessions | [API](./references/api.md) |
| Localhost proxy, runtime config or PCF serving | [Serving](./references/serving.md) |

Load `stack-profile` before recommending runtime, tooling or infrastructure choices. Use
[starting code](#starting-code) selectively: equivalent app or library facilities satisfy the
contract.

## Build the complete workflows

Get one working end-to-end path through the running backend early, then complete every required
workflow and its loading, empty, success, error and stale states. Use a typed client for the
backend's actual contract (generate from OpenAPI when available); coordinate backend changes
through `api-craft`. Mocks and labelled sample data support development and tests; any integration
they replace remains an explicit gap.

- **Recoverable failures.** Route and independent-panel error boundaries contain failures in place
  without dropping the page heading. Every async path ends in a rendered state. Show an actionable
  error, a copyable request ID, time and zone, and safe retry; report boundary catches and
  unhandled rejections to browser error reporting with request ID and release, without secrets.
- **State ownership.** Server state lives in the query cache with visible data age; UI state stays
  local. Put shareable, non-sensitive filters, sort, page and tabs in the URL. Add a global store
  only for state shared by distant components. Choose pagination or virtualization from rendered
  rows, interaction and measured cost; preserve server filtering.
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

Run typecheck, lint, component tests and a production build. Adapt helper assertions to the app's
existing runner: the `.test.ts` assets use `node:test` and must not be copied raw into Vitest.
Do not add a second test runner. Cover applicable [API cases](./references/api.md#contract-tests).

Exercise required workflows against the running backend and run the serving contract on a served
production build. Use the host's Playwright MCP server (or ask the caller when unavailable) to
inspect every view and state in light and dark at desktop width and 320 px; run axe, test keyboard
navigation, and check the console for CSP violations and missing styles. Do not install Playwright
packages or download browsers for MCP verification. Report the brief, workflows, added
dependencies/licences, verification results, screenshots and any unverified gaps.

## Starting code

Copy and adapt only files needed for selected capabilities; reuse equivalent app facilities.

| Capability | Assets and destination |
|---|---|
| App identity | [theme.css](./assets/theme.css) → `src/styles/theme.css` (`@import` right after `@import "tailwindcss"`, or import once before kit styles) |
| API errors | [problem.ts](./assets/problem.ts), [test](./assets/problem.test.ts) → beside the client |
| Idempotency-Key writes | [idempotent-write.ts](./assets/idempotent-write.ts), [test](./assets/idempotent-write.test.ts) → beside the client (imports `problem.ts`) |
| Runtime configuration | [runtime-config.ts](./assets/runtime-config.ts), [test](./assets/runtime-config.test.ts) → bootstrap |
| Served-build checks | [serving-contract.mjs](./assets/serving-contract.mjs) → build configuration |
