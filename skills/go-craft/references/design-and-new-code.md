# Designing and Writing Fresh Go Code

## Layout and Entrypoints

- **Deliverable scale:** Start small utilities in `package main` (split into `internal/<domain>/`
  only when distinct boundaries emerge). For services/CLIs, keep `cmd/<app>/main.go` to a thin
  wrapper calling `run(ctx, os.Args[1:], os.Stdin, os.Stdout, os.Stderr) error` and `os.Exit(code)`.
  Modules at `v2.0.0+` must append `/v2` (or `/vN`) to `module` in `go.mod` and internal imports.
- **No `os.Exit` or `log.Fatal` outside `main()`:** Both skip `defer` across all goroutines and
  prevent in-process `run()` tests.
- **No `init()` side effects or mutable globals:** Never use `init()` for I/O, env reads, logger
  setup, or route registration; never use `http.DefaultServeMux` or package-level mutable singletons.
  Wire `http.NewServeMux()`, `*slog.Logger`, and clients explicitly in `run()`.
- **Anti-bloat and call-site naming:** Never create catch-all packages (`utils`, `common`, `helpers`,
  `models`, `types`, `interfaces`), Java-style layer trees (`domain/ports/inbound`), or unrequested
  DI containers (`wire`, `fx`, `dig`). Avoid package/type stutter at call sites (`yamlconfig.Parse`,
  not `yamlconfig.ParseYAMLConfig`). Omit `Get` on accessors (`u.Owner()`, not `u.GetOwner()`); use
  `Compute` or `Fetch` when a call is expensive or performs remote I/O.

## Interfaces, Types, and Memory

- **Consumer-owned narrow interfaces:** Define 1–3 method interfaces in the *calling* package; return
  concrete structs from `NewX(...)`. Prefer a plain `Options`/`Config` struct over `WithX` functional
  option closures unless most callers pass zero options or options require validation/closures. Keep
  domain logic pure (values + `now time.Time` in, decision + `error` out) so tests use 10-line fakes
  or `func` adapters instead of mock frameworks.
- **Separate wire DTOs from domain types:** Use `*T` or `omitzero` in JSON/patch DTOs where omitted
  vs. zero matters; convert at the edge into validated value-field domain structs.
- **Zero-value and `nil`-slice safety:** Never export a struct whose zero value panics on nil-map
  writes or nil-channel sends; initialize maps in `NewX` or lazy-init on write. Treat `nil` and empty
  slices `[]T{}` identically in function inputs.
- **Typed-nil trap:** Never declare a concrete error pointer (`var err *MyError`) and return it as
  `error` (`(*MyError)(nil)` makes `err != nil` true). Return literal `nil` or declare `var err error`.
- **Slice aliasing and retention:** Slicing a large buffer (`pkt[:16]`) pins the whole backing array
  in GC; copy small retained slices with `slices.Clone` / `bytes.Clone`. Clip capacity with
  `buf[lo:hi:hi]` before passing a sub-slice to code that may `append`.
- **Generics and locks:** Never use type parameters when an interface parameter (`r io.Reader`)
  suffices; never invent `Result[T]`/`Option[T]` monads. Use pointer receivers on structs containing
  `sync`/`atomic` fields and iterate slices of them by index (`for i := range items`).

## Concurrency, Context, and Shutdown

- **Context lifetime:** Pass `ctx context.Context` first; never store it in a struct. For detached
  cleanup that must outlive request cancellation, use
  `detCtx, cancel := context.WithTimeout(context.WithoutCancel(ctx), budget)` with `defer cancel()`,
  never bare `context.Background()` (drops trace/`slog` values) or unbounded `WithoutCancel`. Always
  `defer stop()` immediately after `stop := context.AfterFunc(ctx, fn)`.
- **Goroutine and channel traps:**
  - Prefer synchronous functions over helpers that spawn hidden background goroutines; let callers
    add concurrency (`errgroup.Group` with `SetLimit(n)`, `wg.Go`, or a semaphore). Every worker
    channel send must select on `<-ctx.Done()` if the receiver can exit early.
  - **`errgroup.WithContext`:** `gctx` is canceled when the first worker errors *and* when `g.Wait()`
    returns—never pass `gctx` to post-`Wait()` cleanup or commit calls.
  - **Closed-channel `select` spin:** In `for { select { case v, ok := <-ch: ... } }`, a closed
    channel yields `(zero, false)` immediately and spins at 100% CPU unless `if !ok { ch = nil }`
    disables the case.
  - **Multi-producer fan-in:** Only the coordinator closes the shared output channel after `wg.Wait()`.
  - **Shutdown sequence:** (1) `signal.NotifyContext`, (2) `srv.Shutdown(drainCtx)` *before*
    canceling dependencies in-flight handlers use, (3) `g.Wait()`, (4) close DB/clients in reverse order.

## Errors, I/O, and Persistence

- **Error boundary and formatting:** Format error strings lowercase without trailing punctuation and
  place `%w` at the end (`"open config: %w"`). Use `%w` when callers inspect via `errors.Is` /
  `errors.AsType` / `errors.As`; use `%v` across module boundaries to keep internal drivers private.
  Log at the top handler OR return with context—never both.
- **Writable `Close()` and atomic files:** Check `Close()` on writable files/streams
  (`defer func() { err = errors.Join(err, f.Close()) }()`). Write critical files via
  `os.CreateTemp(dir, ".tmp-*")` in the *same directory*, `Sync()`, `Close()`, then `os.Rename`.
- **Bounded reads and SQL:** Bound untrusted streams with `io.LimitReader(r, max+1)` or
  `http.MaxBytesReader`. Check `err != nil` on `db.BeginTx(ctx, opts)`, then immediately
  `defer tx.Rollback()`. Always `defer rows.Close()` outside loops and check `rows.Err()`.

## Post-Cutoff Go 1.22–1.26+ Capabilities and Traps

| Floor | Use | Trap / Rule |
|---|---|---|
| 1.22+ | Per-iteration loop vars; `http.ServeMux` `"GET /items/{id}"`; `slices.Concat`, `slices.DeleteFunc` | `ServeMux` `"/"` matches every unmatched subtree; use `"/{$}"` for exact `"/"`. `"GET "` also matches `HEAD`. Always reassign `s = slices.DeleteFunc(s, fn)` |
| 1.23+ | `iter.Seq`/`Seq2`; `slices.Collect`/`SortedFunc`/`Chunk`; `maps.Keys`/`Values`/`Collect`; timer fixes | Stdlib `maps.Keys(m)` returns `iter.Seq[K]`, **not** `[]K` (materialize with `slices.Collect` or `slices.Sorted`). `Timer.Stop()`/`Reset()` clears stale channel entries—never run legacy `if !t.Stop() { <-t.C }` drains (deadlocks) |
| 1.24+ | `os.OpenRoot`; `json` `omitzero`; `strings.SplitSeq`/`Lines`; `slog.DiscardHandler`; `crypto/rand.Text()`, `crypto/hkdf`, `crypto/pbkdf2`, `crypto/sha3`; `runtime.AddCleanup`; `go.mod` `tool`; `b.Loop()`; `t.Context()`/`t.Chdir()` | Prefer `omitzero` over `omitempty` to omit zero `time.Time{}` and `IsZero() bool` structs. In `runtime.AddCleanup(ptr, fn, arg)`, `fn` must **never** capture `ptr` or it leaks. Use `strings.SplitSeq` in `for range` to avoid `[]string` allocation |
| 1.25+ | `wg.Go(fn)`; `testing/synctest`; expanded `os.Root` (`ReadFile`, `WriteFile`, `MkdirAll`, `RemoveAll`, `Rename`); `reflect.TypeAssert[T]`; `slog.GroupAttrs`; `http.NewCrossOriginProtection()`; `go.mod` `ignore`; `go vet` `waitgroup` & `hostport` | `wg.Go(fn)` handles `Add(1)` and `defer Done()`. Format dial addresses with `net.JoinHostPort(host, port)`, never `fmt.Sprintf("%s:%d", ...)` (`hostport`) |
| 1.26+ | `new(expr)` pointer init; `errors.AsType[E]`; `slog.NewMultiHandler`; `t.ArtifactDir()`; `signal.NotifyContext` cause; self-referential generic constraints; `go fix` modernizer & `//go:fix inline` | Use `new(30)` / `new(true)` instead of `ptr[T]` helpers. Prefer `errors.AsType[*MyErr]` over `errors.As`. Do not import `encoding/json/v2` unless `GOEXPERIMENT=jsonv2` is enabled |
