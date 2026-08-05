# React — identity, effects, ownership, and server/client boundaries

Read this for React UI code. The universal frontend rules live in `skills/frontend-craft/SKILL.md`,
and the universal TypeScript language rules live in the `language-idiom` skill loaded alongside it.
On any conflict, those owners and the target repository win.

## Contents

- Establish the React contract
- State is minimal and identity is structural
- Hooks and Effects
- Composition and escape hatches
- Errors, Suspense, and async work
- SSR and hydration
- Security boundaries
- Performance and testing
- Verify
- Primary evidence anchors

## Establish the React contract

- Read the target package's `package.json`, lockfile, renderer, framework configuration, and build
  plugins first. React, `react-dom`, the router/framework, the test renderer, and any compiler must
  be compatible; a workspace-root dependency does not prove the touched package uses it.
- Determine whether the target is client-rendered, SSR/hydrated, React Server Components, or a
  mixture. A rule that is safe in a Vite SPA may cross a server/client boundary in a framework app.
- Match the repository's component, data-fetching, styling, form, routing, and test conventions.
  Adding React code is not authority to migrate class components, enable React Compiler, replace
  the query layer, or adopt a new framework API.
- Component render functions are pure: same props, state, and context produce the same JSX. Do not
  mutate inputs, read changing globals, start work, or write to the DOM during render.

## State is minimal and identity is structural

- **Compute derived values during render.** Do not copy props or existing state into another state
  variable through an Effect. Store the smallest source of truth; derive filtered lists, labels,
  and totals directly, memoizing only measured expensive work.
- State behaves as a snapshot for one render. When the next value depends on the previous value,
  use a functional update (`setCount(count => count + 1)`), especially across queued updates.
- Never mutate objects or arrays held in state. Replace the changed path so React receives a new
  value; a shallow copy is insufficient when nested objects are still mutated.
- A component's type, position, and `key` determine state identity. Never define a component inside
  another component: each render creates a new type and remounts it. Hoist the definition and pass
  data explicitly.
- List keys come from stable domain identity—not array position, randomness, or `useId`. A key
  change intentionally resets the component subtree; an accidental change loses focus and state.
- Give each piece of state one owner. Choose controlled or uncontrolled behavior deliberately;
  mirroring a controlled prop into local state creates two authorities.
- Boolean props multiply possible states. When combinations become invalid or hard to name, use
  explicit variant components or a discriminated variant prop that makes allowed states visible.

## Hooks and Effects

- Call ordinary Hooks at the top level of a component or custom Hook, before early returns. Do not
  call them in loops, conditions, event handlers, class components, or callbacks passed to other
  Hooks. Keep the hooks linter enabled.
- React 19's `use` API has different rules: it may be conditional, but it still runs only inside a
  component or Hook and cannot be wrapped in `try/catch`. Do not emit it for an older React target.
- **An Effect synchronizes with an external system.** Derived rendering data belongs in render;
  user-triggered writes belong in the event handler; parent notification normally belongs in the
  same event. If no external system is being synchronized, remove the Effect.
- Effect dependencies are determined by the reactive values the Effect reads. Do not suppress the
  exhaustive-deps rule to force a desired schedule; change the code, stabilize the real dependency,
  or move non-reactive event logic out of the Effect.
- Setup and cleanup are one reversible process. Remove listeners, disconnect subscriptions, clear
  timers, and abort or retire stale work. Strict Mode re-runs render, Effects, and ref callbacks in
  development to expose impurity and missing cleanup; fix the lifecycle instead of disabling it.
- Use the repository's router/framework loader or query/cache layer (TanStack Query in this
  skill's default stack) for server data. A manual fetch Effect needs cancellation or stale-result
  suppression, error/loading state, caching, and a plan for waterfalls and server rendering.
- Subscribe to an external mutable store through `useSyncExternalStore` or the repository's
  established wrapper rather than recreating subscription state with ad hoc Effects.
- A custom Hook shares stateful logic, not one state instance. Name it `use...`, keep its return
  contract small, and let each call own its state unless a provider/store intentionally shares it.

## Composition and escape hatches

- Prefer ordinary children for structural composition. A render prop is justified when the parent
  supplies per-item state or behavior; a component factory hidden in render recreates identity.
- Compound components can share a provider contract shaped around state and actions. The provider
  boundary—not visual nesting—grants access. Split contexts or stabilize provider values when
  unrelated consumers otherwise rerender together.
- Refs are escape hatches for imperative focus, measurement, or integration—not a parallel state
  store. Expose the smallest imperative handle and keep normal data flow declarative.
- React 19 accepts `ref` as a regular prop. React 18 and earlier require `forwardRef` for function
  components, and `forwardRef` remains callable in React 19. Check the installed major version and
  do not mass-migrate established ref code as incidental cleanup.
- React 19's `use(Context)` can read context conditionally; `useContext` remains a valid ordinary
  Hook. Do not describe one as an unconditional replacement for the other.

## Errors, Suspense, and async work

- Put error boundaries around meaningful failure domains — the per-panel boundaries the Resilience
  UX rules require. They catch errors from descendant render and lifecycle work, but not event
  handlers, arbitrary async callbacks, server rendering, errors in the boundary itself, or failures
  outside the tree.
- A boundary fallback is designed state with retry/reset behavior and observability. Root
  `onCaughtError`, `onUncaughtError`, and `onRecoverableError` callbacks can report production
  failures when the installed renderer supports them.
- Suspense coordinates work supported by React or the target framework. Do not create a new Promise
  during every render; promises consumed with `use` must be cached and rejected work belongs under
  an error boundary.
- Mark non-urgent rendering with the repository's transition pattern only when it preserves input
  responsiveness. A transition is not a network timeout, cancellation policy, or error handler.

## SSR and hydration

- The server and first client render must produce identical markup. Treat hydration warnings as
  bugs: browser-only branches, random IDs, current time, locale/timezone differences, invalid HTML,
  and mutable external data are common causes.
- Browser globals and DOM-dependent work belong behind an explicit client boundary or in an Effect.
  Effects do not run during server rendering.
- Never store request/user state in mutable server module scope. Server modules are shared across
  requests; pass request data through arguments or a correctly keyed/request-scoped cache.
- Use `useId` for stable accessibility relationships such as `aria-describedby`, with consistent
  server/client prefixes when multiple roots exist. It is not a list key or a cache key.
- `suppressHydrationWarning` is a narrow one-level escape hatch for an unavoidable mismatch, not a
  repair strategy. Test the hydrated result and retain production recoverable-error reporting.
- Values crossing a server/client or Server/Client Component boundary must follow the framework's
  serialization contract. Do not pass secrets, database handles, or arbitrary class instances.

## Security boundaries

- React escapes interpolated text, not arbitrary HTML. Use `dangerouslySetInnerHTML` only for
  content sanitized by an explicitly owned policy; never treat "came from our API" as sanitization.
- Validate or allowlist user-controlled navigation targets and URLs before rendering or following
  them. A component cannot make an unsafe URL safe by escaping text around it.
- Do not place secrets in props, client bundles, serialized server-component payloads, or hydration
  data. A value rendered to the client is public to that client.

## Performance and testing

- Profile before memoizing. `memo`, `useMemo`, and `useCallback` are performance tools with their
  own dependency and comparison costs; they are not semantic requirements. Match a repository using
  React Compiler rather than layering speculative manual memoization over it.
- Keep props stable at expensive boundaries and subscribe at the granularity consumed. Split routes
  and genuinely heavy widgets, virtualize measured large lists, and verify the production bundle.
- Test observable behavior through accessible roles, labels, text, and user interactions (React
  Testing Library + MSW in this skill's default stack). Avoid assertions on Hook order, private
  state, or component internals.
- Exercise Effect cleanup, stale async results, error-boundary reset, Strict Mode development
  behavior, and state preservation/reset where those contracts changed.
- SSR work gets a server-render plus hydration test with recoverable errors captured. Every changed
  primary flow still gets the real-browser and keyboard pass required by the frontend-craft gate.

## Verify

Run the target package's declared typecheck, lint, unit/component tests, production build, and
browser flow. Record the installed React/renderer versions and whether the exercised path was
client-only, server-rendered, or hydrated. A component test alone does not prove hydration, bundle,
or browser behavior.

## Primary evidence anchors

- Keeping components pure: <https://react.dev/learn/keeping-components-pure>
- Choosing and structuring state: <https://react.dev/learn/choosing-the-state-structure>
- State identity and keys: <https://react.dev/learn/preserving-and-resetting-state>
- Rules of Hooks: <https://react.dev/reference/rules/rules-of-hooks>
- Removing unnecessary Effects: <https://react.dev/learn/you-might-not-need-an-effect>
- Effect lifecycle and cleanup: <https://react.dev/learn/lifecycle-of-reactive-effects>
- Strict Mode checks: <https://react.dev/reference/react/StrictMode>
- External-store subscriptions: <https://react.dev/reference/react/useSyncExternalStore>
- Error boundaries:
  <https://react.dev/reference/react/Component#catching-rendering-errors-with-an-error-boundary>
- Hydration contract: <https://react.dev/reference/react-dom/client/hydrateRoot>
- Stable accessibility IDs: <https://react.dev/reference/react/useId>
- React 19 ref behavior: <https://react.dev/reference/react/forwardRef>
- React `use`: <https://react.dev/reference/react/use>
