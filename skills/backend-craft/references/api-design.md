# API surface design

Read this before shaping endpoints, resource names, status codes, list-query conventions, or a
published API evolution. The universal backend rules live in `../SKILL.md`; they win on conflict.

SKILL.md already carries the method semantics, the status-code meanings, the `202`-plus-status-
resource rule for long-running work, and the cursor-pagination default — those are core, not
conditional, and are not restated here. This file owns what SKILL.md leaves open: naming, the cursor
*mechanics*, how domain errors reach the one problem shape, and how a published surface evolves.

## Naming and shape

- URLs are plural kebab-case nouns. Nest one ownership level when it clarifies the relationship
  (`/v1/users/{id}/orders`); deeper nesting encodes a join the client should be making by ID.
- Reserve verb-y paths for genuine non-CRUD actions (`POST /v1/orders/{id}:cancel`).
- `POST` is non-idempotent unless the operation implements an idempotency key.

## List mechanics

- Filter with allowlisted query fields; parameterize values. Choose one multi-value and range
  convention and keep it across the API.
- Use a stable sort ending in a unique key. An opaque cursor contains the ordered key values, not
  an offset. Fetch `limit + 1` to learn whether a next page exists, cap `limit` server-side, and omit
  total counts unless they are cheap — a count on a large table is a full scan per page.

## Typed errors reach the wire

- Domain code raises typed errors carrying a stable code and HTTP status. One global exception
  mapper emits the top-level RFC 9457 problem shape from `../SKILL.md`. Handlers do not build
  problem bodies by hand; that is how a second error shape gets born.
- Unexpected exceptions log full internal detail with the request ID and return a generic problem.
  SQL, stack traces, credentials, and upstream bodies never cross the API boundary.
- Enumerate stable problem types and codes in OpenAPI; renaming one is a breaking change.

## Evolving the surface

- Extend rather than mutate: add optional fields/parameters and new endpoints. Removing, renaming,
  changing a type, tightening auth, or making an existing optional field required is breaking and
  requires an explicit compatibility plan.
- Deprecation is a protocol, not a comment: announce it, publish a sunset date, observe callers, and
  retire only after the supported migration window. SKILL.md's two-live-versions and `Sunset`/`410`
  rules are the mechanics.
- Diff the OpenAPI document in CI with a breaking-change detector. A removal, type change, or new
  required field cannot merge as an unlabeled accident.
