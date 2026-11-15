# Tooling and verification

## Project setup

- Start with [`uv init --python <floor>`](https://docs.astral.sh/uv/) (`--lib` for a library);
  without `--python` the floor becomes whatever interpreter uv finds. Confirm `[build-system]` in
  the result; uv before 0.12 needs `--package`.
- `[project.scripts]` and installing the project need a build backend: `uv_build` for pure Python,
  another for extension modules or build scripts.
- Dependency groups never reach
  [published metadata](https://packaging.python.org/en/latest/specifications/dependency-groups/);
  extras do.
- Applications deploy from the lock: `uv sync --locked --no-default-groups`, or `uv export` for
  another installer. `--no-dev` drops only the `dev` group.
- Libraries test declared lower bounds in CI with
  `uv run --isolated --resolution lowest-direct pytest`. It can rewrite `uv.lock`, even with
  `--isolated` on older uv: restore the lock afterwards and never commit the rewritten one.

## Tool configuration

- **Ruff** [infers its target](https://docs.astral.sh/ruff/settings/) from `requires-python`; an
  explicit `target-version` overrides it, so delete stale ones. Keep the `UP` rules on so syntax
  tracks the floor; add rules with `extend-select`, because a bare `select` replaces the defaults.
- **Annotations** [evaluate lazily](https://docs.python.org/3.14/whatsnew/3.14.html) on a 3.14+
  floor: add no `from __future__ import annotations` and no quotes around forward references in
  annotations.
- **Type checker:** mypy and pyright infer the Python version from an interpreter, not from
  `requires-python`; set `python_version` or `pythonVersion` to the floor. ty reads the
  `requires-python` minimum. Run the checker in the project environment (`uv run`), where it sees
  installed dependencies.
- **Strictness:** list unmigrated modules as explicit exemptions so the list only shrinks.
  Suppress with a specific error code and a reason, never a blanket ignore.

## Upgrading dependencies

`uv tree --outdated` shows what is behind. `uv lock --upgrade-package <pkg>` moves one package and
`uv lock --upgrade` all, both capped by the constraints in `pyproject.toml`. Raise a constraint
with `uv add '<pkg>>=<new>'`, repeating its `--dev`, `--group`, or `--optional` flag; without it
the package lands in runtime dependencies. Cross a major version one package at a time: read its
migration guide, clear deprecation warnings on the current version, upgrade, then test through the
upgraded API.

## Checks

| Risk | Check |
|---|---|
| Floor or another version | `uv run --locked --isolated --python 3.14 pytest` |
| Layout, entry point, or package-data change | `uv build` (`--no-sources` before publishing), then from outside the source tree `uv run --isolated --no-project --with <wheel> python -c "import <pkg>"`, and run its entry point; checkout tests hide missing files |
| Concurrency | One task forced to fail, cancellation mid-operation, deadline expiry, the bound holding |
| Streaming or bounded memory | Output observed before input is exhausted; cleanup after a consumed prefix |
