# Finding Python defects

Hunt in two passes: a detector for the patterns a linter can see, then a read for the ones it
cannot. A hit is a lead, not a verdict, and a clean run does not clear the code. Reproduce a
suspected defect before reporting it as one; hand an observed failure with an unknown cause to
`root-cause`.

## Run the detector

Use the project's ruff version and configuration, adding the defect rules for this pass only:

```text
ruff check --no-fix --extend-select B,S110,S113,BLE001,DTZ,PLW1510,ASYNC,RUF006,RUF032 <paths>
```

Report hits outside the task instead of fixing them, and leave the project's rule configuration
alone. Without an installed ruff, `uvx ruff check ...` runs it in an isolated tool environment
when the task allows a download.

| Rule | Defect | Operational effect |
|---|---|---|
| `S113` | `requests` call without `timeout` | Requests never times out by default; one stalled peer hangs the job |
| `PLW1510` | `subprocess.run` without `check` | A failed command returns normally and the script reports success |
| `DTZ` | Naive `datetime` (`now()`, `utcnow()`, `strptime` without `%z`) | Stamps shift across hosts and DST; ordering naive against aware values raises `TypeError` |
| `B023` | Closure reads a loop variable | Every callback sees the last value |
| `B006`, `B008` | Mutable default, or a call in a default | State leaks between calls; the default is evaluated once, at definition |
| `B904` | `raise` in `except` without `from` | The traceback reads as a second failure during handling |
| `B012` | `return`, `break`, or `continue` in `finally` | Silences the in-flight exception; Python 3.14 warns at compile time |
| `BLE001`, `S110` | Blind `except Exception`, or `except ...: pass` | Failures become silence or success |
| `ASYNC2xx` | Blocking call (`time.sleep`, `requests`, `open`) in `async def` | Stalls every task on the event loop |
| `RUF006` | `asyncio.create_task` result not kept | The loop holds tasks weakly, so an unreferenced task can vanish mid-flight |
| `RUF032` | `Decimal` from a float literal | `Decimal(0.1)` carries binary error into money |

`PLW1514` (text-mode `open` without `encoding`) is preview-only; on Windows the default is the
locale code page, not UTF-8, so check text I/O that crosses platforms by reading it.

## Read for what the detector cannot see

| Class | Look for | Check |
|---|---|---|
| Edge values | A computed slice start (`items[-n:]` returns everything when `n == 0`), off-by-one ranges, empty input | Call with 0, 1, empty, and more than available |
| Failure reported as success | A handler that logs and returns `None` or `[]`; a loop that continues past failed items; exit 0 after partial failure | Force one item to fail; the caller and exit status must see it (`operator-cli` owns exit codes) |
| Money and rounding | `float` prices or quantities; `round()` on money (half-to-even: `round(2.5) == 2`); `sum()` without a `Decimal` start | Build `Decimal` from strings; quantize with the contract's rounding mode |
| Durations and deadlines | `time.time()` differences for timeouts or elapsed time | Use `time.monotonic()`; wall clocks jump |
| Retries | No attempt cap or total deadline; retried non-idempotent calls | One retry owner with a budget; `backend-craft` owns eligibility |
| Resource lifetime | An iterator returned from inside `with`; a client created per call; a file opened without `with` | Consume the result after the function returns; assert cleanup on failure |
| Shared state | Globals or class attributes mutated from threads or tasks; unbounded caches | Name the owner; bound or lock it |
| Async failures | `gather` raising the first failure while its siblings keep running; `except X` around a `TaskGroup`, which raises `ExceptionGroup` | Force one task to fail and assert the handled path runs |
| Validation by `assert` | `assert` guarding input outside tests | `python -O` strips it; raise an explicit error |

## Fix what you found

Write the failing check first at the public entrypoint the defect reaches: a `pytest` case
parametrized over the boundary values, using `tmp_path`, `monkeypatch`, and an injected clock
rather than real files, environment, or time. Make the smallest change that turns it green, rerun
the affected tests, and report other hits as findings rather than folding them into the fix.

[verified] ruff 0.16.8 fired each listed rule on a scratch fixture, `PLW1514` only with `--preview`;
Python 3.11–3.14 showed `items[-0:]` returning every item, `round(2.5) == 2`, `Decimal(0.1)` carrying
binary error, and naive/aware ordering raising `TypeError`.
[sourced] [ruff rules](https://docs.astral.sh/ruff/rules/),
[Requests timeouts](https://requests.readthedocs.io/en/latest/user/advanced/#timeouts),
[asyncio tasks](https://docs.python.org/3/library/asyncio-task.html),
[time.monotonic](https://docs.python.org/3/library/time.html#time.monotonic), and
[decimal](https://docs.python.org/3/library/decimal.html).
