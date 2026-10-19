---
name: go-craft
description: >-
  Write, refactor, modernize, or test Go in services, CLIs, libraries, and workers.
  Load before editing Go, including module upgrades and concurrent code. Triggers:
  'build this in Go', 'refactor this Go package', 'modernize this Go module',
  'test this Go worker'. Not for runtime-only operations; use incident-investigation for
  incident troubleshooting. Compose with api-craft for HTTP and operator-cli for command contracts.
argument-hint: "[Go code, package, or task]"
---

# Go craft

Load `stack-profile` for toolchain choices, `api-craft` for HTTP boundaries, and `operator-cli`
for command contracts. Keep language changes within the requested task; preserve caller-visible
behavior unless its change is intentional.

## Establish the version boundary

- Inspect `go.mod`, an active `go.work`, build tags, CI and deployment targets. The `go` directive
  sets the module's minimum Go version and language semantics; `toolchain` suggests a preferred
  toolchain, not a new compatibility floor. File build constraints can raise the effective version.
- For new modules and scoped upgrades, verify the latest compatible stable Go and dependency
  releases against official docs and upstream evidence. Explain constraints that require older
  versions. Review changes to `go` and dependencies after module commands; a dependency upgrade
  can raise the minimum version. Preserve required `GOOS`, `GOARCH`, and cgo support.
- For modernization on Go 1.26+, preview `go fix -diff` on the affected packages. Apply only the
  intended transformations and inspect affected callers; do not combine an unrelated module-wide
  rewrite with a defect fix. The modernizers respect effective file versions, but a successful
  build with a newer compiler alone does not establish support for the oldest promised toolchain.

## Preserve Go contracts

- Before refactoring, identify exported callers, error matching through `errors.Is`/`errors.As`,
  ownership of shared slices/maps, and serialized or persisted data. Check nil versus empty values,
  aliasing and ordering when replacing custom code with standard-library operations.
- When choosing `encoding/json/v2` (Go 1.27+), test the actual wire or stored-data contract:
  nil slices/maps encode as empty arrays/objects by default, field matching is case-sensitive,
  `omitempty` uses JSON emptiness, and duplicate object names or invalid UTF-8 are rejected.
  `encoding/json` remains supported; adopting v2 is a behavior change to assess, not an automatic
  consequence of upgrading Go.

## Own concurrent work

- Give each goroutine an owner, a termination path and a completion signal. Cancellation requests
  a stop; it does not join goroutines. Unblock canceled work, then join it before releasing resources
  it still uses. Test cancellation while admission is full and while work is in flight.
- Bound admission before spawning; a semaphore inside one goroutine per item still permits
  unbounded waiting goroutines. If using `errgroup`, `SetLimit` makes `Go` block for capacity
  without observing cancellation. Use cancellation-aware admission when the caller must stop
  promptly. The `WithContext` context is canceled when `Wait` returns, even on success; use the
  parent or a separately owned context for subsequent work.

## Verify the changed behavior

- Run the project's format, vet and test checks on affected packages and callers. For a claimed
  minimum Go version, test with that toolchain and automatic toolchain switching disabled;
  check required build tags and platform variants. Use `go test -race` for changed shared state
  on a supported target; it checks executed paths, not every possible schedule.
- On Go 1.25+, use `testing/synctest.Test` for suitable time/concurrency tests instead of sleeps
  that guess when a goroutine has progressed. `synctest.Wait` means other bubble goroutines are
  durably blocked, not finished. Keep real network I/O out of fake-time assumptions; test that
  integration separately. Verify the cancellation and completion conditions themselves.
