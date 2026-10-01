# Finding Python defects

Inspect the relevant code and use an available detector for patterns it can recognize. A hit is a
lead, not a verdict, and a clean run does not clear the code. Establish expected behavior and the
cause of a suspected failure; reproduce it where possible and distinguish evidence from uncertainty.

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
| Shared state | Globals or class attributes mutated from threads or tasks; unbounded caches | Name the owner; bound or lock it |
| Async failures | Unowned tasks, swallowed cancellation, or an individual-error handler around grouped failures | Force one task to fail; check sibling lifetime, cleanup, and handling of the actual exception shape |
| Text I/O | An implicit encoding where files cross machines or processes | Read and write non-ASCII text under the required encoding; do not assume the host's default |
| Validation by `assert` | `assert` guarding input outside tests | `python -O` strips it; raise an explicit error |

## Fix what you found

When a fix is requested, capture a failing check at the entrypoint the defect reaches, using the
project's test conventions and independent expected behavior. Control irrelevant time, randomness,
and external effects, while keeping real boundaries that the check needs to exercise. Verify the
smallest sufficient repair and relevant failure paths; report material adjacent findings separately.

[sourced] [ruff rules](https://docs.astral.sh/ruff/rules/),
[Requests timeouts](https://requests.readthedocs.io/en/latest/user/advanced/#timeouts),
[asyncio tasks](https://docs.python.org/3/library/asyncio-task.html),
[time.monotonic](https://docs.python.org/3/library/time.html#time.monotonic), and
[decimal](https://docs.python.org/3/library/decimal.html).
