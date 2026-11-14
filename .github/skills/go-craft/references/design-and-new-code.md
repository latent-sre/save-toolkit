# Designing and Writing Fresh Go Code

## Layout and Entrypoints

- **Deliverable scale:** Start small utilities in `package main` (split into `internal/<domain>/`
  only when distinct boundaries emerge). For services/CLIs, keep `cmd/<app>/main.go` to a thin
  wrapper calling `run(ctx, os.Args[1:], os.Stdin, os.Stdout, os.Stderr) error` and `os.Exit(code)`.
- **No `os.Exit` or `log.Fatal` outside `main()`:** Both skip `defer` and block in-process `run()` tests.
- **No `init()` side effects or mutable globals:** Never use `init()` for I/O, env reads, logger
  setup, or route registration; never use `http.DefaultServeMux` or package-level mutable singletons.
  Wire `http.NewServeMux()`, `*slog.Logger`, and clients explicitly in `run()`.

## Interfaces, Types, and Memory

- **Consumer-owned narrow interfaces:** Define 1–3 method interfaces in the *calling* package; return
  concrete structs from `NewX(...)`. Prefer a plain `Options`/`Config` struct over `WithX` functional
  option closures unless most callers pass zero options or options require validation/closures. Use
  10-line fakes or `func` adapters in tests instead of mock frameworks.
- **Separate wire DTOs from domain types:** Use `*T` in input/patch DTOs where omitted vs. zero
  matters (`omitzero` only affects marshaling); convert at the edge into validated value-field
  domain structs.
- **Slice aliasing and retention:** Slicing a large buffer (`pkt[:16]`) pins the whole backing array
  in GC; copy small retained slices with `slices.Clone` / `bytes.Clone`. Clip capacity with
  `buf[lo:hi:hi]` before passing a sub-slice to code that may `append`.

## Concurrency, Context, and Shutdown

- **Context lifetime:** For detached cleanup that must outlive request cancellation, use
  `detCtx, cancel := context.WithTimeout(context.WithoutCancel(ctx), budget)` with `defer cancel()`,
  never bare `context.Background()` (drops trace/`slog` values) or unbounded `WithoutCancel`. Always
  `defer stop()` immediately after `stop := context.AfterFunc(ctx, fn)`.
- **Goroutine and channel traps:**
  - Prefer synchronous functions over helpers that spawn hidden background goroutines; let callers
    add concurrency (`errgroup.Group` with `SetLimit(n)`, `wg.Go`, or a semaphore). Every worker
    channel send must select on `<-ctx.Done()` if the receiver can exit early.
  - **`errgroup`:** `gctx` is also canceled when `g.Wait()` returns—never use it afterwards. Under
    `SetLimit`, `g.Go` blocks for a slot without observing cancellation.
  - **Shutdown sequence:** (1) `signal.NotifyContext`, (2) `srv.Shutdown(drainCtx)` *before*
    canceling dependencies in-flight handlers use, (3) `g.Wait()`, (4) close DB/clients in reverse order.

## Errors, I/O, and Persistence

- **Error boundary:** Use `%w` when callers inspect via `errors.Is` / `errors.As`; use `%v` across
  module boundaries to keep internal drivers private. Log at the top handler OR return with
  context—never both.
- **Writable `Close()`:** Check `Close()` on writable files/streams
  (`defer func() { err = errors.Join(err, f.Close()) }()`).
- **Bounded reads and SQL:** Bound untrusted streams with `io.LimitReader(r, max+1)` or
  `http.MaxBytesReader`. Check `err != nil` on `db.BeginTx(ctx, opts)`, then immediately
  `defer tx.Rollback()`.

## Go 1.24–1.26+ Capabilities and Traps

| Floor | Use | Trap / Rule |
|---|---|---|
| 1.24 (skill floor) | Everything through Go 1.24 is baseline: `ServeMux` method and wildcard patterns, `iter.Seq`, `slices`/`maps` iterators, `omitzero`, `os.OpenRoot`, `runtime.AddCleanup`, `go.mod` `tool` | `"GET "` also matches `HEAD`; `"/{$}"` matches only `/`. `maps.Keys` returns `iter.Seq[K]`. Reassign `s = slices.DeleteFunc(s, fn)`. Delete `if !t.Stop() { <-t.C }` timer drains (they can only block). `omitzero`, not `omitempty`, omits a zero `time.Time`. `AddCleanup`'s `fn` must never capture `ptr` |
| 1.25+ | `wg.Go(fn)`; expanded `os.Root`; `http.NewCrossOriginProtection()`; `go vet` `waitgroup` & `hostport` | `wg.Go(fn)` handles `Add(1)` and `defer Done()`. Format dial addresses with `net.JoinHostPort(host, port)`, never `fmt.Sprintf("%s:%d", ...)` (`hostport`) |
| 1.26+ | `new(expr)` pointer init; `errors.AsType[E]`; `slog.NewMultiHandler`; `signal.NotifyContext` cause; `go fix` modernizer & `//go:fix inline` | Use `new(30)` / `new(true)` instead of `ptr[T]` helpers. Prefer `errors.AsType[*MyErr]` over `errors.As`. `encoding/json/v2` is still an experiment here (`GOEXPERIMENT=jsonv2`); do not import it below `go 1.27` |
