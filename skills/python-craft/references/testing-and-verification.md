# Python Environment, Testing, and Quality Gates

## `uv`, Lockfile, and Floor Traps

- **Bind the project interpreter first:** Inspect `.python-version`, `requires-python`, CI matrix, lockfiles, and `.venv`. Never run bare `python`, `py`, or `pytest` on `PATH` (especially Windows Store stubs or global installs).
- **`uv run --locked` vs. `--frozen` / `--no-sync`:** For `uv` projects, run `uv run --locked <cmd>` (verifies lockfile freshness without editing `uv.lock`); `--frozen` skips freshness checks and `--no-sync` can run against stale site-packages, so neither is equivalent validation.
- **`uv pip sync` and `uvx` traps:** Never run `uv pip sync` with a sparse test requirements file against a shared venv (it uninstalls unlisted packages); use `uv pip install -r ...`. Run `mypy`, `pyright`, and import checks in the project environment rather than an isolated `uvx` environment that cannot see project dependencies.
- **Floor validation:** Check changed syntax and stdlib APIs against `requires-python` (`ruff check --target-version py312`, `mypy --python-version 3.12`) and run tests on the floor interpreter when available.

## Verification Traps and High-Signal Checks

| Changed surface or risk | Non-obvious check or trap |
|---|---|
| Undertested legacy refactoring | Pass characterization tests before editing that pin values, **exact runtime types** (`0 == Decimal("0")` and `0 == False` are `True`—assert `isinstance(res, Decimal)`), input non-mutation, and exception types/messages |
| Custom-code replacement or library migration | Differential tests comparing old vs. new outputs/errors across boundary and malformed inputs (`0`, `-0`, `bool`-as-`int`, `NaN`/`Infinity`, non-ASCII UTF-8) in isolated `tmp_path` fixtures without duplicating side effects |
| Parsers, normalizers, or conservation laws | `hypothesis` `@given(...)` property tests or deterministic `itertools.product` sweeps for round-trip, idempotence, and conservation invariants |
| Streaming, generator lifetime, or lookup scaling | Assert incremental yield before full consumption, file closure on exhaustion/`.close()`/decode error, borrowed iterators never closed, and deterministic operation counts (counted `__eq__`/`__hash__` or `tracemalloc`) instead of wall-clock timings |
| Module moves, splits, or release archives | Fresh-process imports in both orders (`python -c "import a, b"` and `"import b, a"`), plus building/installing the wheel or release archive (`release.zip`) and executing entrypoints outside the source checkout |
| Dependency addition or upgrade | Lockfile check (`uv lock --check`), fresh import smoke test, license check, and `pip-audit` when available (clean audit checks known CVEs only) |

## Execution Discipline

- Run focused tests, `ruff check --no-fix --no-fix-only`, `ruff format --check`, and configured type checking; scope unavoidable `# type: ignore[code]` suppressions to a single line and code with a rationale.
- Run the final verification command standalone in the foreground after your final edit without piping or backgrounding so exit status and full output remain visible.
