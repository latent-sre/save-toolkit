# Writing Python

Judge design at its callers: clear intent, visible effects, and fewer facts to coordinate. Function
length, argument count, and caller count are signals, not limits.

## Simplify calls

- Name the operation and its effects. Prefer clear options such as `write_report(rows, overwrite=False)`.
  Keyword-only options help prevent ambiguity; adding `*` or renaming parameters can break existing callers.
- Group values that form one concept with shared invariants, such as a valid date range. An arbitrary
  options bag or `**kwargs` hides independent knobs without removing their complexity.
- Derive redundant arguments only when meaning, ownership, and evaluation timing agree. Current
  length differs from a requested limit, snapshot, or independently supplied count requiring validation.
- Separate unrelated flag-selected operations; keep genuine options. Return meaningful related values
  or explicit outcomes instead of tuples whose meaning changes by mode. Preserve supported result contracts.
- Pass needed clients, clocks, and settings rather than the whole application context or globals.
  Use a `Protocol` for a meaningful interchangeable boundary; a callable/concrete dependency may suffice.

## Functions and modules

- Extract a coherent decision, shared policy, or effect boundary, even for one caller. Keep steps
  together when splitting shuttles intermediates around. Inline empty forwarding layers; retain useful
  validation, compatibility, instrumentation, and resource ownership.
- Separate calculations from I/O where callers benefit, keeping effect/failure order visible.
  Extraction alone does not improve the algorithm or representation.
- Classes suit shared state, invariants, or lifecycle ownership; stateless operations often suit
  functions. Prefer composition over inheritance solely for reuse. Factories need construction policy.
- Group related responsibilities and dependencies; move a concept with its supporting details.
  Avoid catch-all utilities and one file per tiny helper. Check consumers before moving public names.

## Data and typing

- Records can remove coordination between parallel values. Choose dataclasses when their generated
  construction/equality fits, or `TypedDict` to retain a dict API. Neither supplies runtime type validation.
- Type useful boundaries, narrow `Any`, and validate external input. Distinguish missing, `None`, zero,
  false, and empty. Require only needed collection behavior; iterators may be single-pass.
- Make copying, sharing, and mutation deliberate. Avoid mutable defaults; use `field(default_factory=list)`
  for dataclass lists. `frozen=True` does not recursively freeze contained collections.
- Preserve numeric and time contracts: construct exact `Decimal` values from appropriate text/integers,
  choose precision/rounding, use monotonic clocks for durations, and distinguish UTC instants from local
  calendar rules needing their original zone.

## Errors and resource ownership

- Keep `try` narrow; catch expected errors. Translate at meaningful boundaries with `raise ... from exc`;
  do not turn unrelated failures into success. Log where handled, with redaction, avoiding repeated logs.
- Owners close resources; borrowers preserve them. Clean up on failure/cancellation and keep lazy
  consumers inside the resource lifetime. Initialize at lifecycle boundaries, avoiding import-time effects.
- For async code, avoid event-loop blocking, own tasks, bound concurrency/queued work, and propagate
  cancellation after cleanup. `TaskGroup` (3.11+) is not a concurrency limit or a drop-in `gather` replacement:
  ordinary failures are grouped. `except ValueError` misses grouped members; `except Exception` catches
  `ExceptionGroup`. Handle inside tasks or use `except*`; its handler cannot exit via `return`, `break`,
  or `continue`. Apply one operation deadline: `asyncio.timeout()` on 3.11+, or `wait_for()` around the
  combined coroutine on 3.10; do not reset the deadline per await.

[sourced] [parameters](https://docs.python.org/3/tutorial/controlflow.html#special-parameters),
[typing](https://docs.python.org/3/library/typing.html),
[dataclasses](https://docs.python.org/3/library/dataclasses.html),
[decimal](https://docs.python.org/3/library/decimal.html),
[datetime](https://docs.python.org/3/library/datetime.html#datetime.UTC),
[exceptions](https://docs.python.org/3/tutorial/errors.html), and
[async tasks](https://docs.python.org/3/library/asyncio-task.html).
