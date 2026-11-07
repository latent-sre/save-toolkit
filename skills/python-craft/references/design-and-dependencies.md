# Design and dependencies

## New code

Before substantial capability, settle these; decide them directly for a small utility, without a
design document.

| Decision | Guidance |
|---|---|
| Floor and consumers | `requires-python`, the CI matrix, and deployment targets, never the host's newest Python |
| Layout | Script: one module with `main(argv=None) -> int` and PEP 723 metadata for isolated dependencies; no `pyproject.toml` or `src/` scaffolding. CLI: importable core, thin argument/IO adapter, `[project.scripts]`. Service: transport, configuration, and policy in separate modules. Library: `src/` layout, `py.typed`, compatible ranges, explicit exports. In a project: its package root, naming, tests, tooling |
| Boundaries | Entrypoints; typed data; untrusted input validated once at the edge; policy that runs in memory; files, network, subprocesses, clock, and randomness passed in or isolated |
| Lifecycle | Configuration source, state owner, resource lifetimes, failure behavior (partial completion, retries, deadlines) |

Add a module, class, or protocol only for an actual responsibility, lifecycle, integration, reuse,
or change boundary; factories, service layers, hierarchies, DI containers, and extension points need
a present need. Simple still means typed, tested, and complete. Build one path with failures and
cleanup, review its boundaries, then repeat it. Record durable choices (floor, dependency groups,
tool settings, commands) in existing project configuration.

## Python hazards

Diagnostic patterns, not bans: name the consequence before changing one, and keep look-alikes that
do real work, such as a wrapper owning a transaction or a handler translating errors at an
application boundary.

| Pattern | Consequence | Better approach | Verify |
|---|---|---|---|
| `dict[str, Any]` records across modules; broad `Any`; unexplained `cast` or `type: ignore` | Hidden contract | Dataclass, `TypedDict`, enum, or a validating model where coercion is the contract; a narrow `type: ignore[code]` only for a verified third-party typing defect, with its reason | Type checker over callers |
| Dataclass or `TypedDict` trusted to validate; `frozen=True` trusted as deep | Invalid or mutated data | Validate at the boundary; freeze contents | Invalid inputs |
| `bool` as `int`; `float` into `Decimal`; `isalnum`/`isdigit` on non-ASCII; truthiness merging 0, empty, `None` | Wrong values accepted | Explicit rejection; `Decimal` from text with set rounding; `.isascii()`; `is None` | `True`, `0.1`, `"²"`, full-width text, 0, empty |
| Wall clock for durations; naive datetimes | Jumps, zone errors | `time.monotonic()`; aware datetimes; UTC instants kept apart from local calendar rules in their original zone | Controlled clock |
| Iterating an input twice; `if items:` on a generator; `sum` of empty `Decimal` values | Empty second pass; generators are always truthy; empty sum is `int` 0 | Consume once or materialize deliberately; `sum(xs, Decimal(0))` | Generator and empty inputs |
| Mutable default; exposed internal collection; module-level mutable state | Leakage, aliasing | Fresh object per call; one explicit owner; injected clock, config, clients | Repeated calls in one process |
| Import-time network, writes, or required environment reads | Import order and tools break | Initialize at lifecycle entry | Fresh-process import |
| `assert` validating input | Stripped by `-O` | Explicit error | Run under `-O` |
| Broad `except` that logs and continues or reports success; dropped context | Failure reported as success | Specific catches; translate at boundaries with `raise ... from exc`; report partial completion | Force one item to fail |
| Unbounded retries, no deadline, retried non-idempotent effects, nested retry owners | Duplicate effects, amplification | One owner, bounded attempts, per-call I/O timeouts inside one overall deadline (a stop rule never interrupts a blocking call); retry only idempotent or deduplicated effects; reconcile an unknown outcome before replay | Count physical attempts |
| Unowned tasks; blocking calls in async code; swallowed `CancelledError` | Leaks, hangs | `TaskGroup` (3.11+) or owned tasks, bounded concurrency, re-raise cancellation after cleanup, one deadline per operation (`asyncio.timeout()`, 3.11+, else `wait_for`); `TaskGroup` is no concurrency limit or drop-in `gather`: it cancels siblings on the first failure and raises `ExceptionGroup`, so handle inside tasks or use `except*` | Fail and cancel one task |
| File without `with`; client per call; lazy result returned from inside `with` | Leaks, closed-resource errors | Owners close, borrowers preserve; consume lazy results inside the lifetime | Consume after return; failure cleanup |
| State shared across threads or tasks; unbounded cache | Races, growth | Name the owner; lock or bound it; the GIL does not make compound updates atomic | Concurrent test |
| Implicit text encoding | Host-dependent decoding | Explicit encoding and malformed-input policy in the IO adapter; file and stdin decoding can differ | Non-ASCII and invalid bytes through each real path |

## Dependencies

- Prefer by fit: an existing project capability; the standard library when it meets behavioral,
  operational, and maintenance needs without substantial scaffolding; then a maintained package.
  Unless a stated constraint forbids packages (such as a `python -I -S` hook), do not hand-roll
  substantial parsing, validation, HTTP, retry, or similar machinery, and never add a package that
  duplicates an existing capability.
- Before a material addition, replacement, or upgrade, verify: distribution and import identity and
  capability; version-appropriate public APIs from primary docs or installed source, never memory
  or library internals; Python and platform support (wheels, markers) for every target;
  maintenance by compatibility, responsiveness, and migration guidance, not release frequency;
  license; known advisories; transitive, install, and operational cost. Never send private source
  or credentials while researching. State what could not be verified instead of inventing it;
  reuse evidence for unchanged dependencies.
- The library becomes the implementation owner: delete the custom duplicate; custom code keeps
  business policy, integration, and genuine gaps.
- Separate runtime dependencies, optional extras, and development groups (`[dependency-groups]`);
  libraries publish compatible ranges, applications lock. Change declarations and locks only through
  the project's manager (`uv lock`, `poetry lock`, `pip-compile`); never hand-edit a lock, upgrade
  unrelated packages, or switch managers as cleanup. Keep the previous state installable, and
  transformation tools out of runtime dependencies.
- For an unconstrained new project, evaluate uv, Ruff, pytest, and one maintained type checker.
  Keep adequate existing tooling; never add a duplicate (flake8, black, isort beside Ruff).
- For a replacement, compare coercion, defaults and missing versus `None`, exception types
  (translate to what callers catch), ordering and duplicates, serialization, numeric precision and
  rounding, redirects, timeouts, retries, sync/async behavior, and cleanup. Traps: Pydantic strict
  and lax modes accept different inputs; HTTPX and Requests differ in redirect and timeout defaults
  and exceptions; Tenacity's bare decorator retries forever without waiting and, without
  `reraise=True`, ends in `RetryError` rather than the original exception. Never silently tighten
  accepted inputs during cleanup.

## Modernization

Modern means supported on every target runtime and beneficial, not newest; new syntax must parse on
the oldest supported interpreter, and a backport cannot add grammar. Dropping
`from __future__ import annotations` or unquoting forward references is safe only when every
supported runtime is 3.14+; under that import annotations are strings, which Pydantic and
`get_type_hints` must resolve and dataclasses only text-match for `ClassVar` and `InitVar`.
Dataclass `slots`, `kw_only`, and `frozen` can break assignment, positional construction, pickling,
and subclasses. Preview upgrades with Ruff `UP` at the component's real `--target-version`.
