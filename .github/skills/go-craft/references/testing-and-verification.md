# Go Testing, Concurrency Verification, and Quality Gates

## Risk-to-Verification Matrix

| Changed surface or risk | Required check |
|---|---|
| Any code creation, bug fix, or refactor | `go test -count=1 <pkgs>` and `go vet <pkgs>` |
| Goroutines, channels, mutexes, `atomic`, `errgroup`, workers, or caches | `go test -race -count=1 <pkgs>` exercising concurrent callers and cancellation/shutdown |
| Undertested legacy code before refactoring | Passing characterization tests pinning outputs, JSON `[]` vs `null`, and error contracts |
| Parsers, binary framing, custom unmarshalers, or path normalizers | Fuzz test (`func FuzzX(f *testing.F)`) checking round-trip/invariants (`-fuzz=^FuzzX$ -fuzztime=5s`) |
| Allocation or throughput optimization | Before/after benchmark (`go test -bench=^BenchmarkX$ -benchmem`) |
| Cross-platform path, process, or signal code | Target compile/vet check (`GOOS=linux GOARCH=amd64 go vet ./...` and `go test -c`) |

## Subtest and Lifecycle Traps

- **No branching trees in table subtests:** Split happy-path and error/validation cases into
  separate tables when setup or assertions diverge. Match errors via `errors.Is` or
  `errors.AsType[T]` (Go 1.26+) / `errors.As`, never `err.Error()` substrings.
- **Failure messages and `t.Error` vs. `t.Fatal`:** Format diagnostics as `f(%v) = %v, want %v`
  (**`got` before `want`**) or `cmp.Diff(want, got)` (`-want +got`), without third-party `assert.*`
  wrappers. Use `t.Errorf` to report all independent mismatches in a test; reserve `t.Fatalf` for
  preconditions where continuing would panic or cascade.
- **Never call `t.Fatal` / `t.FailNow` in a child goroutine:** `FailNow` calls `runtime.Goexit()` on
  the child goroutine only, hanging or corrupting the test. Use `t.Errorf(...)` and return, or
  propagate errors back via `errgroup` / channel.
- **`t.Parallel()` teardown and fixture isolation:**
  - When subtests call `t.Parallel()`, the outer `TestX` returns *before* subtests run—a plain
    `defer teardown()` in `TestX` destroys shared state while subtests execute! Register shared
    teardown with `t.Cleanup(teardown)`.
  - Instantiate mutable fixtures (buffers, maps, structs, DB transactions) inside each `t.Run` body.
  - `t.Setenv` and `t.Chdir` panic if called alongside `t.Parallel()`; inject config/paths instead.
- **Go 1.24–1.26+ `testing.T` helpers:**
  - **`t.Context()` (1.24+):** Cancels automatically *just before* `t.Cleanup` functions run, so
    workers stop before `t.Cleanup` tears down databases or temp dirs.
  - **`t.TempDir()` on Windows:** Fails cleanup if any `*os.File` inside the dir remains open—treat
    this as a leaked file handle in the code under test.
  - **`t.ArtifactDir()` (1.26+):** Persists failure dumps when `go test -artifacts` is passed.

## Deterministic Concurrency (`testing/synctest`)

Never use wall-clock `time.Sleep` to coordinate goroutines or test timeouts.

- **Go 1.25+ `synctest.Test(t, func(t *testing.T) { ... })`** (never use Go 1.24's experimental
  `synctest.Run(func())`):
  - Runs an isolated bubble with a synthetic clock (`2000-01-01 00:00:00 UTC`) that advances
    **instantly** whenever all bubble goroutines are durably blocked (on channels, `select`,
    `sync.Mutex`, `sync.WaitGroup`, or `time.Sleep`).
  - Call `synctest.Wait()` to pause until all other bubble goroutines are durably blocked, then
    assert intermediate state deterministically.
  - **Exit deadlock trap:** If any bubble goroutine remains durably blocked when the root function
    returns, `synctest.Test` panics (`deadlock: main bubble goroutine has exited but blocked goroutines remain`).
    Always cancel/stop workers and wait for exit before returning.
  - **OS I/O boundary:** Real sockets (`net.Listen`), OS file locks, and subprocesses are *not*
    durably blocked in a bubble; use `net.Pipe()` or channels.
- **Go <= 1.24:** Inject a clock/ticker function or synchronize with barrier channels and
  `context.AfterFunc`. Test cancellation both before call start and mid-flight.

## Race Detector and Benchmarks (`b.Loop`)

- **`-race` execution requirement:** `-race` detects races only on code paths executed concurrently
  during that run, and requires `CGO_ENABLED=1` plus a C compiler. If a C toolchain is unavailable,
  run `go test -count=1 ./...` and report `-race` as unverified due to missing C toolchain.
- **`for b.Loop()` (Go 1.24+):** Runs pre-loop setup once per invocation, resets the timer on entry,
  and prevents dead-code elimination. **Trap:** Never call `b.StopTimer()`, `b.StartTimer()`, or
  `b.ResetTimer()` before or inside `for b.Loop()`—stopping the timer fails fatally with
  `B.Loop called with timer stopped`.
