# Finding Python defects

Detector hits are leads, not verdicts; clean output does not establish correctness.

## Optional Ruff detector

When Ruff is available, use the project's version and configuration. This selection adds common
defect leads for the current pass without editing rule configuration:

```text
ruff check --no-fix --no-fix-only --extend-select B,S110,S113,BLE001,DTZ,PLW1510,ASYNC,RUF006,RUF032 <paths>
```

Both disabling flags are required for a check-only run when a project may configure `fix-only`.
Check the installed version's rule availability and ignored/excluded paths before relying on the
result. Read individual findings in context: a subprocess caller may inspect `returncode`, a loop
closure may be consumed immediately, and a naive datetime may represent an intentional local value.
Use existing tools when Ruff is absent; acquiring a new tool is a separate environment decision.

## Read for what the detector cannot see

| Class | Look for | Check |
|---|---|---|
| Edge values | A computed slice start (`items[-n:]` returns everything when `n == 0`), off-by-one ranges, empty input | Call with 0, 1, empty, and more than available |
| Failure reported as success | A handler that logs and returns an empty result, ignored command status, or partial failure hidden from the caller | Force one item to fail; check the specified partial-result and error/exit contract |
| Numeric contracts | Binary-float error in exact decimal work, wrong rounding policy, empty totals changing type | Use an appropriate representation; `Decimal` from strings avoids float conversion error, and a `Decimal` sum start preserves the empty-result type |
| Durations and deadlines | `time.time()` differences for timeouts or elapsed time | Use `time.monotonic()`; wall clocks jump |
| Retries and timeouts | Missing I/O timeouts, no attempt/deadline budget, or retried non-idempotent effects | Establish eligibility and a bounded overall operation; account for nested retry owners |
| Resource lifetime | An iterator returned from inside `with`; a client created per call; a file opened without `with` | Consume the result after the function returns; assert cleanup on failure |
| Shared state | Globals or class attributes mutated from threads or tasks; unbounded caches | Name the owner; bound or lock it. Do not rely on the GIL for compound-update atomicity, including when moving to free-threaded builds |
| Async failures | Unowned tasks, swallowed cancellation, or an individual-error handler around grouped failures | Force one task to fail; check sibling lifetime, cleanup, and handling of the actual exception shape |
| Text I/O | An implicit encoding where files cross machines or processes | Exercise the real byte boundary with non-ASCII input; host defaults do not establish the protocol encoding |
| Validation by `assert` | `assert` guarding input outside tests | `python -O` strips it; raise an explicit error |

Use `root-cause` for diagnosis; verify repairs through the affected entrypoint and failure paths.
