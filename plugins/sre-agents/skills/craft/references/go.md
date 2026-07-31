# Go craft

Match the repo's existing tooling first; defaults below apply when none is set.

## Style & tooling
- **Format with `gofmt`** (non-negotiable — enforce in CI); use `goimports` (superset that also fixes
  imports). Don't hand-format.
- **Vet with `go vet`** for static correctness; **lint with `golangci-lint`** — baseline `staticcheck`,
  `govet`, `errcheck`, `ineffassign`, `unused`; broaden with `revive`, `gosec`, `gocyclo`, `unparam`.
- **Accept interfaces, return concrete types.** Small interfaces. Doc comments are full sentences
  starting with the symbol name.

## Error handling (Go 1.13+)
- Return errors; don't `panic` for ordinary failures, and don't `_ =` them away.
- Wrap with `fmt.Errorf("...: %w", err)` **only when you mean to expose** the underlying error (it
  becomes part of your contract — Hyrum's Law); use `%v` otherwise.
- Inspect with `errors.Is` (sentinel match through the chain) and `errors.As` (extract a concrete type).
- Handle the error where you have the context to act on it.

## Concurrency
- "Share memory by communicating" — prefer channels to pass ownership; use `sync.Mutex` when it's
  simpler. `sync.WaitGroup` to wait on goroutines.
- **`context.Context`** for cancellation/deadlines: pass it as the first arg; **always `defer cancel()`**
  after `WithCancel/WithTimeout/WithDeadline` to avoid goroutine/timer leaks. Goroutines should exit
  promptly on cancel/timeout — never leak one waiting on an un-cancelled context.

## Correctness traps
- Naked returns in long funcs; ignored errors. (Loop-variable capture in closures/goroutines was a
  classic trap, but **Go 1.22+ gives each iteration its own variable** — only watch for it on Go <1.22.)
- Nil-map writes; unbounded result sets; not closing `rows`/`Body`/files (`defer Close()`).

## Tests
- **Table-driven** with `t.Run` subtests; stdlib `testing` (`t.Errorf`/`t.Fatalf`, no assertion lib
  needed). Run `go test -race` on anything concurrent (≈10× cost, so target it, not always-on). Native
  fuzzing (`func FuzzXxx`) for parsers/encoders. See the [tests-first process](./tdd.md).

## Modules & versioning
- **Semantic Import Versioning:** v2+ carries a `/v2` suffix in the module path and imports. Released
  versions are immutable. Run `go mod vendor` to build `vendor/`; once it exists and is consistent, `go`
  commands use it automatically (the `-mod=vendor` default) — **but only for modules whose `go.mod`
  declares `go >=1.14`**; older modules need an explicit `-mod=vendor`.

## Definition of done
`gofmt`/`goimports` clean · `go vet` + `golangci-lint` clean · `go test ./...` (with `-race` where
relevant) green.
