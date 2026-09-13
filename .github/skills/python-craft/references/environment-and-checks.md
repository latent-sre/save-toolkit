# Python environment and checks

Read before selecting an interpreter, installing development tools, or running checks. The existing
project workflow wins; `stack-profile` supplies defaults where none exists. uv manages Python
versions, environments, and packages; it does not replace the Python interpreter or prove a refactor.

## Bind the environment before the baseline

Inspect the runtime floor, CI matrix, `.python-version`, manifests, lock/constraint files, and
existing virtual environment. A developer's newest Python is not necessarily a supported target.
Record the selected interpreter's `sys.executable` and `sys.version`; run baseline and candidate
checks through that same environment. Bare `python`, `py`, `pip`, and an editor may select different
installations. Use `python -m pytest` through the verified interpreter rather than an unrelated
`pytest` on PATH. Verify changed syntax on the component's actual runtime floor too.

| Existing workflow | Use | Preserve |
|---|---|---|
| uv project with `pyproject.toml` and `uv.lock` | `uv run --locked python -m pytest`, with the project's test paths/options | Required extras/groups and locked dependencies; a missing/stale lock is an error to resolve explicitly |
| Requirements and constraints | Create/reuse a project venv, install the intended requirements set with `uv pip install --python <venv-python> -r <requirements-file>`, then run that interpreter | Constraints, markers, indexes, and separate test/development requirements |
| Poetry, another manager, or a supplied environment | The repository's documented commands | Do not migrate the package manager as part of cleanup |

For a Windows project that explicitly requires Python 3.14, with no existing venv:

```powershell
uv venv --python 3.14 .venv
uv pip install --python .venv\Scripts\python.exe -r requirements-test.txt
.venv\Scripts\python.exe -c "import sys; print(sys.executable); print(sys.version)"
.venv\Scripts\python.exe -m pytest -q
```

Choose the project's actual version and requirements file; on POSIX use `.venv/bin/python`.
Reuse an existing matching environment rather than recreating it. Install/download only within
the task's authority; absence of the required interpreter is a gap, not a reason to test a substitute.

## Keep environment changes visible

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

## Compare useful evidence

Run affected tests plus the configured lint/type checks before and after the change. Preserve
baseline failures as named gaps; do not silence rules, weaken annotations, or broadly rewrite tests
to make the new result green. Test public callers and relevant failure paths, then the appropriate
broader suite. Report tool/interpreter versions when they change the result.

[sourced] [uv project locking and syncing](https://docs.astral.sh/uv/concepts/projects/sync/),
[environment selection](https://docs.astral.sh/uv/pip/environments/), and
[requirements installation versus synchronization](https://docs.astral.sh/uv/pip/compile/);
[isolated tool environments](https://docs.astral.sh/uv/guides/tools/).
