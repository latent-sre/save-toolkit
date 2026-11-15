# Tooling and verification

Check a flag that matters against the [uv documentation](https://docs.astral.sh/uv/).

## Project setup

- Start with `uv init`: `--package` for an installable application or CLI, `--lib` for a library.
- uv installs the project itself, and `[project.scripts]` works, only with `[build-system]`
  declared. `uv_build` covers pure Python; extension modules or build scripts need another backend.
- `uv add <pkg>` for runtime, `uv add --optional <extra> <pkg>` for a published extra,
  `uv add --dev <pkg>` or `--group <name>` for development. Dependency groups never reach
  [published metadata](https://packaging.python.org/en/latest/specifications/dependency-groups/);
  extras do.
- Applications deploy from the lock (`uv sync --locked --no-dev`, or `uv export` for another
  installer) and raise bounds freely. Libraries upgrade the lock but raise a published lower bound
  only when the code needs the newer API; test those bounds in CI with
  `--resolution lowest-direct`. Upper bounds only for known incompatibilities.

## Tool configuration

- **Ruff** infers its target from `requires-python`; an explicit `target-version` overrides it, so
  delete stale ones. Enable the `UP` rules so syntax tracks the floor.
- **Annotations** evaluate lazily from 3.14: do not add `from __future__ import annotations` or
  quote forward references.
- **Type checker:** mypy and pyright default to the running interpreter's version; set
  `python_version` or `pythonVersion` to the floor. ty reads the `requires-python` minimum. Run
  the checker in the project environment (`uv run`), where it sees installed dependencies.
- **Strictness:** strict mode project-wide. For existing untyped code, list the unmigrated modules
  in per-module overrides so the list only shrinks. Suppress with a specific error code and a
  reason, never a blanket ignore.

## Upgrading dependencies

`uv tree --outdated` shows what is behind. `uv lock --upgrade-package <pkg>` moves one package and
`uv lock --upgrade` all, both capped by the constraints in `pyproject.toml`. Raise a constraint
with `uv add '<pkg>>=<new>'`, repeating its `--dev`, `--group`, or `--optional` flag; without it
the package lands in runtime dependencies. Cross a major version one package at a time: read its
migration guide, clear deprecation warnings on the current version, upgrade, then test through the
upgraded API.

## Commands

| Purpose | Command |
|---|---|
| Floor or another version | `uv run --locked --isolated --python 3.14 pytest` |
| Built artifact | `uv build`, then from outside the source tree `uv run --isolated --no-project --with <wheel> python -c "import <pkg>"`, and run its entry point; checkout tests hide missing files |

## Risk to check

| Risk | Check |
|---|---|
| Concurrency | One task forced to fail, cancellation mid-operation, deadline expiry, the bound holding |
| Streaming or bounded memory | Output observed before input is exhausted; cleanup after a consumed prefix |
