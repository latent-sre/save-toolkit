# Refactoring, Fixing, and Modernizing Existing Go Code

## Execution Loop

1. **Map contracts and non-compiler consumers:** Separate external contracts (Mandate 4) from internal
   implementation. Before renaming or deleting, search non-static consumers: struct tags,
   `//go:generate` (`stringer`, `mockgen`, `sqlc`, `protoc`), `//go:embed`, `reflect`, and
   `text/template` / `html/template`.
2. **Pin behavior at the entrypoint:** Run `go test -count=1 <pkgs>` for a baseline. Add passing
   characterization tests (undertested code) or a failing reproduction test (bug fix) through the
   exported entrypoint—never against private helpers being reshaped, and never codifying a bug.
3. **Transform completely:** Apply the smell table across the touched scope and update all in-repo
   callers.
4. **Retire dead code:** Delete superseded unexported code per the `SKILL.md` table; on Go 1.26+,
   add `//go:fix inline` to `// Deprecated: use X.` bridges for external callers.
5. **Verify improvement:** Run `go fix -diff ./...` (or `modernize`), `go vet ./...`, and
   `go test -count=1 <pkgs>` (add `-race` when concurrent code or shared state changed). Confirm
   concrete gain: one policy owner, pure domain logic testable without I/O, bounded goroutines, or
   simpler caller signatures.

## Smell-to-Transformation Table

| Smell in touched code | Transformation | Guardrail |
|---|---|---|
| Handler/CLI/worker mixes SQL/HTTP/OS I/O, clock reads, and domain rules | **Extract pure core:** `func evaluate(in Input, now time.Time) (Decision, error)`; keep outer method as thin I/O shell | Preserve validation-before-I/O order and error wrapping |
| Internal `type FooService interface` + `fooServiceImpl` with 1 implementation | **Collapse interface:** Delete producer interface, export `*FooService`, put 1–3 method interfaces at consumer sites | Keep only if exported to external repos or multi-implementation |
| Bare `go func()` without lifecycle, error path, or concurrency cap | **Structured concurrency:** `errgroup.WithContext(ctx)` + `SetLimit(n)`, or `wg.Go(fn)` (1.25+); wait on shutdown | Never pass `errgroup`'s `gctx` to post-`Wait()` calls; `g.Go` under `SetLimit` blocks without observing `ctx` |
| Racy `if s.c == nil` init or verbose `sync.Once` + fields | **`sync.OnceValue` / `OnceValues`:** Store `OnceValues` func on the struct | `OnceValues` caches errors permanently; use mutex/`singleflight` if transient failures must retry |
| `map[string]any` bags or 5+ coupled parameters | **Domain struct:** Replace with typed struct (and constructor check if invariants exist) | Preserve wire `json`/`db` tags at serialization boundaries |
| Manual slice/map/sort/min-max/split loops | **Stdlib replacement:** Run `go fix` / `modernize` (`slices`, `maps`, `cmp`, `min`/`max`, `clear`) | Check `null` vs `[]` JSON marshaling on empty slices |

## Equivalence Traps

1. **JSON `null` vs. `[]`:** A nil slice marshals as `null`, an empty one as `[]`. `var out []T` and
   `slices.Collect` of an empty sequence give `null`; `slices.DeleteFunc` keeps `[]` but zeroes the
   tail in place—clone first if the slice is aliased.
2. **`iter.Seq` contract:** Return as soon as `yield` returns `false` (continuing panics); always
   `defer stop()` after `iter.Pull`.

## High-Signal Defect Checklist

| Defect | Look for | Fix |
|---|---|---|
| Unchecked iterator error | `for rows.Next()` / `scanner.Scan()` returning `nil` after loop | Check `rows.Err()` / `scanner.Err()` after loop |
| HTTP body leak / unbounded read | `defer resp.Body.Close()` before `err != nil`, missing on non-2xx, or raw `io.ReadAll` | `Close` after `err != nil` on every status code; bound with `io.LimitReader(resp.Body, max+1)` |
| Zero-timeout client / leaked `sql.Tx` | `http.Get`, `&http.Client{}` without `Timeout`, or `BeginTx` without `defer tx.Rollback()` | Set `http.Client{Timeout: ...}` + `ctx`; `defer tx.Rollback()` after `err != nil` check |
| `defer` in loop / `time.After` in loop | `defer Close()`/`Unlock()` in `for`; `<-time.After(d)` in hot `select` loop (allocates a timer per iteration) | Extract loop body to helper; hoist `time.NewTimer(d)` and `Reset(d)` |
| Integer narrowing (`gosec` G115) | Casting `int`/`int64`/`uint64` to `int32`/`uint16`/`uint` unchecked | Check bounds against `math.Max*` and `>= 0` first |
| Leaked internal collection | Returning struct field `s.items` (`[]T` or `map[K]V`) directly | Return `slices.Clone(s.items)` / `maps.Clone(s.m)` |

## Automated Modernization and Linters

- **`go fix` (Go 1.26+) and `modernize`:**
  - Go 1.26+ toolchain: `go fix -diff ./...` (preview) and `go fix ./...` (apply; `-<name>=false` skips a pass).
    It offers only rewrites the module's `go` line allows (a `go 1.24` module gets no `wg.Go` or
    `new(expr)`).
  - Go <= 1.25 toolchain: `go run golang.org/x/tools/go/analysis/passes/modernize/cmd/modernize@latest -fix -diff ./...` (preview; drop `-diff` to apply; never use the retired `gopls/internal/...` path).
- **`golangci-lint` and `govulncheck`:** Use repo config. Run `govulncheck ./...` after dependency
  changes.
