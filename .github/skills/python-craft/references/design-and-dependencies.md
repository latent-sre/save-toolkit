# Design, Modern Python, and Dependencies

## Designing New Code Before Weak Patterns Spread

- **Consumers and runtime floor**: check `requires-python`, deployment targets, CLI/import consumers, and OS limits.
- **Smallest layout**: keep small utilities as one script or module; use `pyproject.toml`, `src/<package>/`, explicit `__all__`, and `py.typed` when packaging, entrypoints, or multi-module distribution warrant them.
- **Explicit boundaries**: separate pure domain policy and typed models (`dataclass(frozen=True, slots=True)`, `NamedTuple`, `TypedDict`, `Enum`, `pydantic`) from boundary validation, CLI parsing, and I/O.
- **Patchable entrypoints and streaming I/O**: expose `main(argv: Sequence[str] | None = None) -> int` resolving collaborators at call time so monkeypatches work; stream large inputs line-by-line; return exit codes (`0` success, `2` usage/input error); pass `encoding="utf-8"` (`newline=""` for CSV) and reject `NaN`/`Infinity` in strict JSON (`allow_nan=False`).
- **State and resources**: inject config, clocks, randomness, and clients explicitly; bind files, sockets, locks, temp paths, and subprocesses to `with` / `async with` or `ExitStack`.
- **Earned structure**: add classes, `Protocol`, or modules only for a real lifecycle, state, I/O seam, or change boundary. Deliver one complete path (including errors and cleanup) before repeating a pattern.

## Modern Python Features

Select idioms supported by `requires-python`:
- **3.10+**: `match`/`case`, `X | Y` unions, `dataclass(slots=True, kw_only=True)`, `zip(..., strict=True)`.
- **3.11+**: `asyncio.TaskGroup`, `asyncio.timeout`, `except*`, `tomllib`, `StrEnum`, `Self`, `add_note()`.
- **3.12+**: `type` aliases, PEP 695 generics (`def f[T](x: T) -> T`), `@override`, `itertools.batched`, `Path.walk()`.
- **3.13–3.14+**: `@warnings.deprecated()`, `Queue.shutdown()`, PEP 649/749 deferred annotations on 3.14+ (omit `from __future__ import annotations` on 3.14+ unless supporting `<3.14` or string-annotation consumers).

## Libraries and Dependency Decisions

- **Inspect existing capabilities** before adding packages or writing substitutes.
- **Prefer stdlib when sufficient** without custom workarounds (`pathlib`, `tomllib`, `json`, `csv`, `sqlite3`, `urllib.parse`, `ipaddress`, `datetime`/`zoneinfo`, `decimal`, `functools`, `itertools`, `collections`, `contextlib`, `subprocess`, `unittest.mock`).
- **Prefer maintained third-party libraries over custom machinery**: stdlib preference is not a zero-dependency rule. Use established packages (`pydantic`, `httpx`, `tenacity`, `click`/`typer`, `hypothesis`, `rich`, `orjson`, `packaging`) over hand-rolled validation, HTTP, retry, or parsing code.
- **Verify additions, replacements, or upgrades**: check package identity, version APIs, Python/OS support, maintenance health (responsiveness/compatibility, not release recency alone), license, advisories, and transitive cost via primary docs or installed source; disclose unavailable facts.
- **Single owner**: let the chosen library own the mechanism; delete parallel custom wrappers or fallbacks.
- **Dependency hygiene**: separate `[project.dependencies]`, `[project.optional-dependencies]`, and `[dependency-groups]`. Keep library constraints compatible while updating app locks (`uv.lock`) via `uv add` / `uv lock`. Never hand-edit lockfiles or upgrade unrelated packages.
- **Defaults**: evaluate `uv`, `Ruff`, `pytest`, and `mypy`/`pyright` for new projects; preserve adequate existing tooling.
- **Replacement semantics**: audit coercion (`bool` subclasses `int`; `ipaddress.IPv4Address` accepts `int`/`bytes` and leading zeros unless gated by `isinstance(v, str)` and digit checks; `Decimal(str(v))` vs `float`), timeouts, exceptions, retry bounds (`@tenacity.retry` needs explicit `stop` and narrow `retry_if_exception_type`), ordering, and cleanup; chain boundary errors with `raise ... from exc`.

## Design, Dependency, and Resource Anti-Patterns

| Anti-pattern | Hazard | Fix |
|---|---|---|
| Speculative layers, pass-through wrappers, single-use ABCs, DI containers | Indirection without a boundary | Delete pass-through layers; call functions or domain types directly |
| Catch-all `utils.py` or god modules mixing parsing, policy, and I/O | Cycles, coupled deps, brittle tests | Split by cohesion; separate pure policy from I/O |
| Mutable defaults, import-time I/O/env reads, mutable globals | State leaks and import side effects | Use `None` or `field(default_factory=...)`; init at startup |
| Unbounded retries, missing timeouts, bare `except Exception:` | Hung workers, retry storms, masked `CancelledError` | Set timeouts, bound retries, `raise DomainError(...) from exc` |
| Unclosed handles or generator functions wrapping `with open(...)` around `yield` | Leaks or premature close | Manage resources in caller `with` blocks or context managers |
