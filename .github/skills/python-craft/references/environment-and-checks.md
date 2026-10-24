# Python environment and checks

Use the target project's supported runtimes and dependency workflow, not the host's newest Python.

## Bind the environment before the baseline

Inspect the runtime floor, CI matrix, `.python-version`, manifests, locks/constraints and existing venv.
Record the selected interpreter's `sys.executable` and `sys.version`; run baseline and candidate
checks through that same environment. Bare `python`, `py`, `pip`, and an editor may select different
installations. Invoke the project's test runner through the intended environment; for pytest,
`<verified-python> -m pytest` avoids an unrelated `pytest` on PATH. Verify changed syntax on the
component's actual runtime floor too, including any isolated standard-library-only entrypoints.

| Existing workflow | Use | Preserve |
|---|---|---|
| uv project with `pyproject.toml` and `uv.lock` | `uv run --locked <project-check-command>` | Required extras/groups and locked dependencies; a missing/stale lock is an error to resolve explicitly |
| Requirements and constraints | Create/reuse a project venv, install the intended requirements set with `uv pip install --python <venv-python> -r <requirements-file>`, then run that interpreter | Constraints, markers, indexes, and separate test/development requirements |
| Poetry, another manager, or a supplied environment | The repository's documented commands | Do not migrate the package manager as part of cleanup |

Reuse an existing matching environment rather than recreating it. Install/download only within
the task's authority; absence of a required interpreter is a gap, not evidence from a substitute.

## When using uv

- `uv run` normally locks and syncs before running. `--locked` prevents a lockfile rewrite and
  checks freshness, but can still change the environment. `--frozen` skips the freshness check;
  it is not stronger validation. `--no-sync` skips environment synchronization and can run stale
  dependencies; use it only with a separately established environment.
- `uv pip install` resolves the requested dependency set and honors constraints. A constraints
  file limits versions; it does not install every package listed in it. `uv pip sync` removes
  packages outside its input and expects the complete resolved set; do not substitute it for
  installing a sparse test-requirements file into a shared development environment.
- Keep refactoring tools in development dependencies. Use the project's versions for repeatable
  checks; a fresh `uvx` tool environment does not automatically contain the project's dependencies.
  A formatter can be standalone; a type/import check must see the intended environment.
- Review manifest/lock changes separately from source cleanup. No `uv init`, dependency upgrade,
  new lock format, or runtime-floor change is implied by a refactoring request.
