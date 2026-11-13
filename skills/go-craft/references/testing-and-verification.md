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
- **Failure messages and `t.Error` vs. `t.Fatal`:** Report `f(%v) = %v, want %v` or
  `cmp.Diff(want, got)` (`-want +got`); no `assert.*` wrappers; `t.Errorf` for independent
  mismatches, `t.Fatalf` only where continuing cascades.
- **Never call `t.Fatal` / `t.FailNow` in a child goroutine:** `FailNow` calls `runtime.Goexit()` on
  the child goroutine only, hanging or corrupting the test. Use `t.Errorf(...)` and return, or
  propagate errors back via `errgroup` / channel.
- **`t.Parallel()` teardown and fixture isolation:**
  - Parallel subtests outlive `TestX`; register shared teardown with `t.Cleanup`, not `defer`.
  - Instantiate mutable fixtures (buffers, maps, structs, DB transactions) inside each `t.Run` body.
  - Inject config/paths rather than using `t.Setenv`/`t.Chdir` under `t.Parallel()`.
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
  - Runs an isolated bubble with a synthetic clock that advances **instantly** when all bubble
    goroutines are durably blocked (bubble channels, `select` on bubble channels, `sync.Cond.Wait`,
    `WaitGroup.Wait` when `Add` ran in the bubble, or `time.Sleep`—**not** `sync.Mutex`/`RWMutex`).
  - Call `synctest.Wait()` to pause until all other bubble goroutines are durably blocked, then
    assert intermediate state deterministically.
  - **Exit deadlock trap:** If any bubble goroutine remains durably blocked when the root function
    returns, `synctest.Test` panics. Always cancel/stop workers and wait for exit before returning.
  - **OS I/O boundary:** Real sockets (`net.Listen`), OS file locks, and subprocesses are *not*
    durably blocked in a bubble; use `net.Pipe()` or channels.
- **Go <= 1.24:** Inject a clock/ticker function or synchronize with barrier channels and
  `context.AfterFunc`. Test cancellation both before call start and mid-flight.

## Race Detector and Benchmarks (`b.Loop`)

- **`-race` execution requirement:** `-race` needs `CGO_ENABLED=1` and a C compiler and only sees
  paths that ran concurrently; without a C compiler, report `-race` unverified.
- **`for b.Loop()` (Go 1.24+):** Runs pre-loop setup once per invocation, resets the timer on entry,
  and prevents dead-code elimination. **Trap:** Never leave the timer stopped when `b.Loop()` is
  next evaluated.
