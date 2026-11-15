# Tooling and verification

uv changes quickly; check a flag that matters against the
[uv documentation](https://docs.astral.sh/uv/).

## Project setup

- Start with `uv init`: `--package` for an installable application or CLI, `--lib` for a library.
- uv installs the project itself, and `[project.scripts]` works, only with `[build-system]`
  declared. `uv_build` covers pure Python; extension modules or build scripts need another backend.
- `uv add <pkg>` for runtime, `uv add --optional <extra> <pkg>` for a published extra,
  `uv add --dev <pkg>` or `--group <name>` for development. Dependency groups never reach
  [published metadata](https://packaging.python.org/en/latest/specifications/dependency-groups/);
  extras do.
- Applications deploy from the lock (`uv sync --locked --no-dev`, or `uv export` for another
  installer). Libraries declare the lowest versions they actually support, and upper bounds only
  for known incompatibilities.
- `.python-version` (`uv python pin`) selects the development interpreter; it does not change
  `requires-python`.

## Tool configuration

- **Ruff** infers its target from `requires-python`; an explicit `target-version` overrides it, so
  delete stale ones. Enable the `UP` rules so syntax tracks the floor.
- **Type checker:** mypy and pyright default to the running interpreter's version; set
  `python_version` or `pythonVersion` to the floor. ty reads the `requires-python` minimum. Run
  the checker in the project environment (`uv run`), where it sees installed dependencies.
- **Strictness:** strict mode project-wide. For existing untyped code, list the unmigrated modules
  in per-module overrides so the list only shrinks. Suppress with a specific error code and a
  reason, never a blanket ignore.

## Commands

| Purpose | Command |
|---|---|
| Checks | `uv run --locked` with `ruff check`, `ruff format --check`, `pytest`, and the type checker |
| Floor or another version | `uv run --locked --isolated --python 3.12 pytest` |
| A library's declared lower bounds | `uv run --isolated --resolution lowest-direct pytest`; `uv.lock` must be unchanged afterwards |
| Built artifact | `uv build`, then from outside the source tree `uv run --isolated --no-project --with <wheel> python -c "import <pkg>"`, and run its entry point |

`--locked` fails on a stale lock. `--frozen` uses a stale lock without complaint.

## Risk to check

| Risk | Check |
|---|---|
| A real boundary: database, HTTP, filesystem, subprocess | An integration test through the real entrypoint, against the real thing or a faithful fake |
| Concurrency | One task forced to fail, cancellation mid-operation, deadline expiry, the bound holding under load |
| Layout, entry point, or package-data change | The built-artifact check; checkout tests hide missing files |
| Dependency upgrade | Tests through the upgraded API surface; its changelog read |
| Streaming or bounded memory | Output observed before input is exhausted; cleanup after a consumed prefix |
