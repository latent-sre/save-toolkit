---
name: frontend-craft
description: >-
  Design, build or improve a web UI — pages, dashboards-as-app-features, forms, admin panels —
  from a static page to a full application, across frameworks. Covers visual design, components,
  interaction, accessibility and resilience UX, including serving a SPA on PCF.
  Triggers: 'build a UI for', 'add a page/form/table', 'make this dashboard page'.
  Not for the service behind the UI (backend-craft) or Grafana/observability dashboards
  (obs-dashboards to design, grafana to operate).
argument-hint: "[the UI to build or change]"
---

# Frontend craft

Deliver a complete, runnable UI, including styles, configuration and wiring. Follow the user's
chosen technology and visual direction; build on the existing project unless the task calls for
changing it. This skill has no framework or library allowlist, package bans, or prescribed look.

Inspect the relevant views, components, manifests, lockfiles and API contracts before editing.
Load `stack-profile` and its application-and-data reference for the actual runtime and language
tooling; the repository's existing tooling wins. A stack inventory does not limit frontend choices.

## Establish the direction

Identify the audience, primary task, representative content, supported devices and browsers, and
what a successful interaction looks like. Infer these from the brief and project; ask only about
unresolved choices that materially change the result. For a new design or redesign, describe a
concise visual direction before building: hierarchy, density, typography, color, imagery and motion.
For a small edit, match the surrounding UI without inventing a separate design exercise.

Choose frameworks, component kits, styling, state and visualization tools for that task. Explain
consequential tradeoffs briefly; an ordinary library or styling choice needs no exception packet.
Use current version-specific documentation when compatibility or behavior is uncertain.

## Build the interaction, including its edges

| Area | Quality to deliver |
|---|---|
| Visual coherence | Use consistent roles for color, type, spacing and emphasis; reuse the project's tokens or define shared values where repetition needs them. Support the themes the product actually needs. If a theme is persisted, apply it before first paint through a CSP-compatible mechanism. |
| Content and states | Use realistic content, clearly distinguishing sample data from live facts. Handle loading, error, empty, success and stale states where applicable; contain a panel failure locally and offer a useful next action. |
| Accessibility | Semantic HTML, labelled inputs, keyboard operation and visible, unobscured focus; AA contrast in shipped themes; status conveyed by text or an icon as well as color. Respect reduced motion. Manage focus on page navigation and dialog open/close; preserve it during same-view updates. Announce saving, completion and errors without stealing focus. |
| State and URLs | Give state a clear owner and lifetime; use local state, shared stores or query caches as appropriate. Keep refreshable/shareable filters, sort, page, tabs and details in the URL when useful; keep credentials, sensitive values and transient drafts out. |
| Forms | Preserve entered values after recoverable failures; associate errors with fields and make submission outcomes clear. Client validation helps the user; server validation remains authoritative. Choose native or library form handling to fit the flow. |
| State-changing actions | Show the exact target and count before a destructive or bulk action and require an explicit confirm; disable the control while the write is pending; send one `Idempotency-Key` per user intent where the API accepts one, reused on retry; show per-item outcomes (including unknown) for bulk actions. |
| Charts and tables | Choose encodings, units, timezones and precision that make the data unambiguous; distinguish zero, missing and stale values. Provide chart text or data-table alternatives. Select pagination or virtualization from interaction needs and measured cost; virtualization does not reduce fetched data. Bound live-series memory and redraw frequency. |

## Verify the result

Run the affected project checks: typecheck/lint, tests for changed behavior, network mocks for
changed requests, and browser automation for critical flows. For a bug, demonstrate the failing
regression first. Use available browser tools to render the changed view, inspect its screenshot,
and exercise its main task and failure states. Fix what that inspection reveals.

Check keyboard interactions, focus and status announcements with assistive technology or available
accessibility tooling. Check affected layouts at 320 CSS pixels (e.g. 400% zoom from 1280); genuinely
two-dimensional content may scroll, but surrounding controls must reflow. Include long labels,
realistic data volumes and the supported themes/viewports relevant to the change. Scale checks to
the task and report what ran and what remains unverified. Install missing verification tools within
the caller's authorized scope; if a browser pass is unavailable, report that gap. A UI never rendered
is written, not verified.

## Load the references needed for the task

| If the view involves… | Read first |
|---|---|
| a new visual direction, redesign or substantial layout change | [design language](./references/design-language.md) |
| choosing or changing frontend tools, or serving a SPA on PCF | [stack selection and serving](./references/stack.md) |
| API requests, untrusted content, caching, authentication, sessions or live updates | [network and sessions](./references/network-and-sessions.md) |

Load every matching row; skip unrelated references.
