# Writing Python

## Simplify calls

- Adding keyword-only `*` or renaming parameters can break supported callers.
- Derive redundant arguments only when meaning, ownership, and evaluation timing agree. Current
  length differs from a requested limit, snapshot, or independently supplied count requiring validation.
- Keep useful single-caller boundaries and forwarding layers that own validation, compatibility,
  instrumentation or resources. Caller count is not a deletion/extraction threshold.

## Data and typing

- Dataclasses and `TypedDict` do not supply runtime type validation; `frozen=True` does not recursively
  freeze contained collections. Preserve missing/None/zero/false distinctions and single-pass inputs.
- Preserve numeric and time contracts: construct exact `Decimal` values from appropriate text/integers,
  choose precision/rounding, use monotonic clocks for durations, and distinguish UTC instants from local
  calendar rules needing their original zone.

## Errors and resource ownership

- Preserve exception chaining at translation boundaries; do not convert unrelated failures into success.
- Owners close resources; borrowers preserve them. Clean up on failure/cancellation and keep lazy
  consumers inside the resource lifetime. Initialize at lifecycle boundaries, avoiding import-time effects.
- For async code, avoid event-loop blocking, own tasks, bound concurrency/queued work, and propagate
  cancellation after cleanup. `TaskGroup` (3.11+) is not a concurrency limit or a drop-in `gather` replacement:
  ordinary failures are grouped. `except ValueError` misses grouped members; `except Exception` catches
  `ExceptionGroup`. Handle inside tasks or use `except*`; its handler cannot exit via `return`, `break`,
  or `continue`. Apply one operation deadline: `asyncio.timeout()` where supported, or `wait_for()`
  around the combined coroutine; do not reset the deadline per await.

## Entrypoints and byte boundaries

Compose `api-craft` for HTTP and `operator-cli` for CLI contracts; language checks do not establish
those boundaries. Use [environment checks](./environment-and-checks.md) for interpreter/dependencies
and `stack-profile` only where project choices are unset.

A UTF-8 file and redirected stdin can use different decoders. Establish encoding, framing and
malformed-input policy, then test valid non-ASCII and rejected bytes through both real paths;
in-memory text tests exercise neither. Keep decoding in the CLI adapter, preserve borrowed streams
and the core's text/record contract. Exercise the real entrypoint; when installation is part of
delivery, check the installed artifact outside the checkout.
