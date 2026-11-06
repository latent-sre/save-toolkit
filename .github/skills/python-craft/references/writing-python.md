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

## Deliverable Classification and Layout Selection

Before writing implementation code, classify the deliverable and select the smallest layout that
supports its execution, import, and testing boundaries:

| Deliverable type | Required layout decision | Packaging rule |
|---|---|---|
| Standalone script or single-module utility | Single `<name>.py` file with focused functions (and a `main(argv: Sequence[str] | None = None) -> int` entry point if CLI-invoked) | MUST NOT create `pyproject.toml`, package directories, `src/` scaffolding, or build backends for a standalone script or isolated single-module utility that has no existing `pyproject.toml`. Optionally use inline script metadata ([PEP 723](https://peps.python.org/pep-0723/)) when isolated script dependencies are needed |
| CLI application | Importable package (`<pkg>/` or `src/<pkg>/`) separating argument parsing/IO from core domain logic, plus `[project.scripts]` entry point | Configure `[build-system]` and `[project]` in `pyproject.toml` ([PyPA pyproject.toml](https://packaging.python.org/en/latest/specifications/pyproject-toml/)) |
| Service or worker | Package separating transport/framework wiring, configuration loading, and pure domain/policy modules | Manage runtime vs. development dependencies and lockfiles for reproducible deployment ([libraries and modernization](./libraries-and-modernization.md)) |
| Reusable library | `src/<pkg>/` layout (prevents accidental uninstalled local imports during testing), explicit `__all__`, and `py.typed` marker ([PEP 561](https://peps.python.org/pep-0561/)) | Define compatibility ranges in `requires-python` and `[project.dependencies]` without pinning consumer applications |
| Component inside an existing project | Module or subpackage matching the repository's established package root, naming, and test layout | Reuse existing `pyproject.toml`, test runner, and lint/type configuration |

## Start with a complete path

Inspect existing modules and dependencies before creating a utility. Establish entrypoints, pure
policy, IO and configuration boundaries; annotate public interfaces and validate external inputs.
Implement and check one end-to-end slice before repeating its structure. Inject clocks, clients,
randomness and streams when their variability matters to the contract or tests.

Reject booleans at integer-only boundaries; reject binary floats when accepting exact decimal inputs.
ASCII-only identifiers need an ASCII check as well as alphanumeric/case checks. Test these at the
actual validation boundary, including rejected inputs.

Create modules, classes and protocols for real responsibility, lifecycle or integration boundaries.
Do not add speculative factories, forwarding managers, dependency-injection containers or deep
package layers to a small utility. Simple code still needs clear types and behavioral tests.
