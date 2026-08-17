# TypeScript — make wrong states hard to represent

Read before writing TypeScript or JavaScript in any layer — including UI work, where this file
loads alongside `frontend-craft`: this file owns the universal language rules; UI state,
accessibility, and resilience UX remain owned by `frontend-craft`.

## Let the compiler carry invariants

- Use branded identifiers when two domain IDs share the same primitive type.
- Represent variants as discriminated unions and exhaustively switch with a `never` check.
- Separate input and output models; server-owned IDs and timestamps do not become optional caller
  fields merely because one interface was reused.
- Keep `strict` enabled. Avoid `any`; narrow `unknown` at the boundary with a schema or type guard.

## Async traps

- Every promise is awaited, returned, or deliberately observed with a rejection handler. Enable
  `no-floating-promises`; `void task()` alone is not error handling.
- Start independent work together and await it with `Promise.all`; do not build accidental network
  waterfalls. Move an await inside the branch that consumes it so early returns remain cheap.
- Bound outbound work with cancellation/timeouts and pass abort signals through client layers.

## State and module boundaries

- Server module scope is process-wide. Store only immutable configuration or deliberately shared,
  correctly keyed caches there; request/user state travels in arguments or request context.
- Prefer direct imports when a barrel loads a large or side-effectful package. Verify that any deep
  import is public and still provides types.
- Keep pure transformations separate from I/O so the invariant-heavy logic is cheap to unit test.

## Writes and retries

- For optimistic cache updates: cancel in-flight reads, snapshot every affected cache, patch,
  restore the exact snapshot on error, and invalidate on settle.
- Do not optimistically perform destructive or money-moving operations. A network error after a
  write is ambiguous; retry only when the same server-enforced idempotency key is reused.
- Mint the idempotency key once per logical action, reuse it through retries, and rotate it only
  after the action settles.

## Tests
- **Vitest or Jest + React Testing Library.** Query by role or text, never by class or test id where
  a role exists — the query is the accessibility assertion. Drive interactions with `userEvent`
  rather than firing synthetic events.
- **Do not test internal state.** Assert what the user observes; a component's state shape is an
  implementation detail and pinning it makes every refactor a test rewrite.
- **Mock the network at the boundary with MSW**, not by stubbing `fetch` per call — the handlers
  stay reusable across tests and keep the component ignorant of the transport.
- **For a SPA GUI**, add Playwright for the few critical user journeys and an accessibility check
  (`jest-axe` or the Playwright equivalent). `frontend-craft` owns the SPA architecture guidance.
- See the [tests-first process](./tdd.md) for the loop these fit into.

## Verify

Run the repository's typechecker, linter (including floating promises), and tests. UI code also
passes `frontend-craft`'s real-browser and accessibility gates.
