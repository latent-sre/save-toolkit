# Writing Python

Choose representations and boundaries that make the required behavior clear. A better data model
or algorithm can remove more complexity than extracting the same logic into smaller functions.
Apply the choices below where they help; avoid arbitrary size/count limits.

## Functions and dependencies

- Name coherent operations, including single-caller helpers; avoid `process_part_2` boundaries.
  Represent unrelated return variants explicitly. Refactoring mechanics live in the parent skill's
  conditional refactoring reference.
- Separate decisions/calculations from I/O where practical; keep effect order in a thin caller.
  Pass clients, clocks, and configuration as ordinary arguments. A dependency-injection framework
  needs a concrete benefit. Use keyword-only options when positional calls obscure meaning.
- Group modules by responsibility. Avoid unrelated `utils.py` helpers, inheritance solely for
  reuse, and interfaces around every function. Use a small `Protocol` when consumers need a shared
  behavioral contract across implementations.

## Data and typing

| Need | Choose deliberately |
|---|---|
| Key-to-value lookup or dispatch | A dictionary with defined missing-key behavior |
| Named internal record | A dataclass when generated construction/equality fits |
| Preserve a dictionary interface with static field checking | `TypedDict`; it remains a dict at runtime |
| Validate external input | The project's boundary validator; evaluate a maintained library for substantial custom validation |
| Consumer access to a collection | An iterable/sequence interface matching repeatability and indexing requirements |
| Money, timestamps, and durations | `Decimal` built from strings; aware UTC `datetime` (`datetime.now(timezone.utc)` on 3.10; `datetime.now(UTC)` on 3.11+); `time.monotonic()` for elapsed time and deadlines |

- Type meaningful boundaries; narrow uncertain inputs rather than spreading `Any`. Annotations
  are not runtime validation. Distinguish missing, `None`, zero, false, and empty values deliberately.
- Make mutation explicit. Avoid shared mutable defaults; use `field(default_factory=list)` for
  per-instance dataclass lists. `frozen=True` does not recursively freeze contained collections.
  Choose copying versus sharing from the contract; neither is universally preferable.
- Use a comprehension for a simple mapping/filter. Keep a loop for multi-step work, per-item
  errors, logging, or effects; side-effect-only comprehensions obscure purpose.

## Errors, resources, and concurrency

- Keep `try` narrow and catch expected errors; do not turn unrelated failures into success.
  Translate errors where callers need a domain error, preserving the cause with `raise ... from exc`.
  Log at the handling boundary with existing redaction; logging/re-raising at every layer duplicates it.
- Owners close files/clients/sessions; borrowers preserve shared resources. Use managed cleanup
  on exceptions and cancellation, and keep lazy consumers within the resource lifetime.
- Initialize resources at the application lifecycle boundary, avoiding import-time network calls,
  thread startup, or application configuration effects.
- Use async when beneficial, without blocking the event loop. Own tasks, bound concurrency and
  queued work, and propagate cancellation after cleanup. On Python 3.11+, `TaskGroup` is neither a
  concurrency limit nor a behavior-equivalent replacement for every use of `gather`: its failures arrive as
  `ExceptionGroup`, so an existing `except X` stops matching. Use `except* X`, whose block cannot
  `return`, `break`, or `continue`, or handle the error inside each task. Put one deadline over
  several awaits with `asyncio.timeout()` on 3.11+. On 3.10, wrap the combined operation in one
  coroutine and apply `asyncio.wait_for()` to it; do not reset the deadline at each await.

[sourced] [typing](https://docs.python.org/3/library/typing.html),
[dataclasses](https://docs.python.org/3/library/dataclasses.html),
[datetime](https://docs.python.org/3/library/datetime.html#datetime.UTC),
[exceptions](https://docs.python.org/3/tutorial/errors.html), and
[async tasks](https://docs.python.org/3/library/asyncio-task.html).
