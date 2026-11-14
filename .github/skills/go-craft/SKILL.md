---
name: go-craft
description: >-
  Design, write, refactor, fix, and modernize Go code across services, libraries, CLIs, workers,
  and tests. Load before writing, editing, or reviewing any Go: build fresh packages right from the
  start, upgrade touched legacy code to modern standards, fix defects, and verify concurrency.
  Compose with api-craft for HTTP APIs/clients and operator-cli for CLI contracts. Triggers:
  'write this in Go', 'refactor this Go code', 'modernize this Go module', 'fix this Go bug'.
  Not for live incident response without code changes (incident-investigation) or non-Go language
  work (python-craft, frontend-craft).
argument-hint: "[Go package, feature, refactor, or defect]"
---

# Go Craft

The task and repository constraints set scope; this skill adds no tools or live authority.
Explanation, design, and review requests stop at those outputs unless implementation is requested.

## Mandates and Leeway

1. **Bind the module floor first.** Read `go.mod` (`go`, `toolchain`, `tool`), any `go.work`, build
   tags, and CI/lint config before choosing features. Never raise the `go` floor without task
   authority, and recheck it after module commands (a dependency upgrade can raise it). This skill
   assumes `go 1.24` or later; on an older module, report that and stay within its floor. On a
   `go 1.27` module, or before moving a toolchain or `go` line to 1.27, read
   [go-1-27.md](./references/go-1-27.md) first.
2. **Build fresh code right from the start.** Keep `main()` as a thin wiring wrapper around a
   testable `run(ctx, ...)` function; separate pure domain decisions from I/O adapters; define narrow
   consumer-owned interfaces; bound every goroutine and resource lifecycle.
3. **Refactor touched code with active leeway.** When fixing a bug, adding a feature, or refactoring,
   clean up structural flaws in the touched scope: flatten deep nesting, extract pure logic from I/O,
   collapse single-implementation producer interfaces, unify duplicated policy, replace custom
   plumbing with `go.mod`-supported stdlib, and fix adjacent resource/concurrency leaks.
4. **Separate internal freedom from external contracts.** Reshape unexported types, helper
   signatures, intra-package file splits, `internal/` packages, and their in-repo callers freely.
   Preserve exported module APIs, wire schemas (JSON tags, `[]` vs `null` slices, SQL schemas, HTTP
   contracts), CLI flags/exit codes, and documented sentinel errors unless authorized to change them.
   Report out-of-scope contract defects separately.

| Rationalization (Reject) | Required Action |
|---|---|
| *"Keep the diff minimal / only patch the broken line"* | Apply Mandate 3 to the touched function and its local helpers |
| *"Match the existing pattern in this file"* | Follow repo conventions (layout, naming, runner), never local defects (naked goroutines, ignored `Close`/`rows.Err`, `map[string]any`, `IFooService` bloat) |
| *"Add a bool flag or drop `ctx` to avoid touching callers"* | Fix the internal signature (`ctx context.Context` first) and update all in-repo callers in one change |
| *"Keep the old unexported helper/interface just in case"* | Migrate all in-repo callers and delete superseded unexported code; use `// Deprecated: use X.` only for exported symbols |
| *"Move shared structs to `common` or `types` to break a cycle"* | Put the type in the package that owns its invariants and define a narrow consumer interface at the lower-level call site |

## Composition and Reference Routing

Compose `api-craft` (HTTP servers/clients/webhooks), `operator-cli` (CLI flags, exit codes, dry-run,
signals), `database-reliability` (migrations/pools), `root-cause` (non-obvious bugs/flakiness), and
`stack-profile` (unset repo tooling).

| Task or inspected code condition | Read |
|---|---|
| New Go binary, package, entrypoint, data model, concurrency/shutdown lifecycle, error/I/O boundary, or Go 1.24–1.26+ features | [design-and-new-code.md](./references/design-and-new-code.md) |
| A `go 1.27` module, moving a toolchain or `go` line to 1.27, `encoding/json/v2`, stdlib `uuid`, or generic methods | [go-1-27.md](./references/go-1-27.md) |
| Refactoring, bug fix, extending legacy Go, replacing custom helpers with stdlib, or running `go fix` / `modernize` | [refactoring-and-modernization.md](./references/refactoring-and-modernization.md) |
| Tests, deterministic concurrency/time (`synctest`), race/leak checks, benchmarks (`b.Loop`), or fuzzing | [testing-and-verification.md](./references/testing-and-verification.md) |

## Guardrails

- Never add blanket `//nolint`, discard actionable write/close/commit/rollback errors with `_ =`,
  weaken valid tests, or claim unexecuted checks passed.
- Report structural changes, preserved contracts, exact commands run (`go test -count=1`, `-race`,
  `go vet`, linters), and any unverified paths.
