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
| Newer stdlib or language feature, changed `go` line, or module upgrade | `go vet <pkgs>` (`stdversion`), then build and test with the floor toolchain under `GOTOOLCHAIN=local`; a newer compiler passing does not prove the floor |

## Test Lifecycle Traps

- **`t.Context()`:** Canceled *just before* `t.Cleanup` functions run. That only signals workers:
  register the `t.Cleanup` that waits for them to exit *last* (cleanups run last-in, first-out) so
  it finishes before databases or temp dirs are torn down.
- **`t.TempDir()` on Windows:** Fails cleanup if any `*os.File` inside the dir remains open—treat
  this as a leaked file handle in the code under test.
- **`t.ArtifactDir()` (1.26+):** Persists failure dumps when `go test -artifacts` is passed.

## Deterministic Concurrency (`testing/synctest`)

Never use wall-clock `time.Sleep` to coordinate goroutines or test timeouts.

- **Go 1.25+ `synctest.Test(t, func(t *testing.T) { ... })`** (never use Go 1.24's experimental
  `synctest.Run(func())`):
  - The bubble clock advances only when every bubble goroutine is durably blocked; `sync.Mutex` /
    `RWMutex` waits do not count. `synctest.Wait()` returns once the others are durably blocked,
    so assert intermediate state after it.
  - **OS I/O boundary:** Real sockets (`net.Listen`), OS file locks, and subprocesses are *not*
    durably blocked in a bubble; use `net.Pipe()` or channels. On Go 1.27+, use
    `httptest.NewTestServer(t, h)` and inject `srv.Client()`: it sends every request, to any host,
    over an in-memory network that works inside a bubble. `Start`/`StartTLS` switch it to a real
    loopback socket.
  - **`synctest.Sleep(d)` (1.27+):** `time.Sleep(d)` followed by `synctest.Wait()`. Use it when the
    test and the code under test sleep for the same duration; with plain `time.Sleep` either may
    run first.
- **`go 1.24` modules:** Inject a clock/ticker function or synchronize with barrier channels and
  `context.AfterFunc`. Test cancellation both before call start and mid-flight.

## Race Detector and Benchmarks (`b.Loop`)

- **`-race` execution requirement:** `-race` needs `CGO_ENABLED=1` and a C compiler (macOS needs
  neither) and only sees paths that ran concurrently; where it cannot run, report `-race`
  unverified.
- **`for b.Loop()`:** Runs pre-loop setup once per invocation, resets the timer on entry,
  and prevents dead-code elimination.
