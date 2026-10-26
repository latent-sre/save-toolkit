# Python Dependency and Packaging Decisions

## Contents

- Deliberate Capability Selection
- Material Dependency Verification Checklist
- Packaging, Groups, and Lockfile Discipline
- Toolchain Candidate Defaults and Improvement Rules
- Semantic Equivalence Checks for Replacements

## Deliberate Capability Selection

When a task requires functionality beyond trivial local code, evaluate these three sources on equal
footing:

1. **Existing project modules and already-installed packages.** Reuse capabilities already in the
   repository or dependency tree before adding a second library for the same job.
2. **Python standard-library modules.** Use supported standard-library facilities (such as `tomllib`,
   `pathlib`, `dataclasses`, `decimal`, `datetime`/`zoneinfo`, `concurrent.futures`, `sqlite3`,
   `urllib.parse`, ` collections`, `itertools`, `functools`, `contextlib`, `unittest.mock`) when they
   solve the problem cleanly without bespoke workarounds.
3. **Maintained third-party packages.** Adopt a maintained library (such as [Pydantic](https://docs.pydantic.dev/)
   for complex schema validation/coercion, [httpx](https://www.python-httpx.org/) for modern sync/async
   HTTP, [Hypothesis](https://hypothesis.readthedocs.io/) for property-based testing, or [Click](https://click.palletsprojects.com/)/[Typer](https://typer.tiangolo.com/)
   for multi-command CLIs) when standard-library code would require hand-rolling substantial protocol,
   retry, validation, or parsing infrastructure.

**Decision rules:**
- You MUST NOT impose a blanket "standard-library-only" or "zero-dependency" rule unless an explicit
  project or runtime constraint requires it (e.g., isolated hook scripts running under `python -I -S`).
- You MUST NOT hand-roll substantial functionality already provided by a suitable maintained library
  without a concrete constraint or cost justification.
- Weigh the ongoing maintenance, bug surface, and testing burden of custom code against the install,
  upgrade, and supply-chain cost of a third-party dependency.

## Material Dependency Verification Checklist

Before adding, replacing, or materially upgrading a dependency, verify and record:

| Verification dimension | What to check |
|---|---|
| Identity and API | Exact package distribution name vs. import name, and the actual API for the installed or target version—MUST NOT guess APIs from memory or package names |
| Python and platform support | Compatibility with the project's `requires-python` range and target OS/architectures (pure-Python wheel vs. native C/Rust extension availability) |
| Maintenance and migration | Release activity, deprecation status, and official changelog/migration notes for major version changes |
| License compatibility | Permissive (`MIT`, `BSD`, `Apache-2.0`) vs. copyleft/commercial restrictions against repository policy |
| Security advisories | Known CVEs/GHSA advisories for the target version (via [`pip-audit`](https://pypi.org/project/pip-audit/) or advisory database when available) |
| Transitive and operational cost | Size of transitive dependency tree, native build tool requirements, and startup/memory overhead |

**Evidence hygiene:**
- Consult primary documentation or installed package introspection (`python -c "import pkg, inspect; ..."`)
  when an API or version behavior is uncertain.
- Do not re-research unchanged dependencies during unrelated code edits.
- When offline or when external sources are unavailable, state what could not be verified rather than
  inventing version numbers, license terms, or advisory status.

## Packaging, Groups, and Lockfile Discipline

Structure dependency declarations in [`pyproject.toml`](https://packaging.python.org/en/latest/specifications/pyproject-toml/)
according to consumer role:

- **Runtime dependencies (`[project] dependencies`):** Only packages required to import and execute
  the production deliverable.
- **Optional user features (`[project.optional-dependencies]`):** Extra feature sets installed by
  downstream users (`pkg[s3]`, `pkg[cli]`).
- **Development groups (`[dependency-groups]`, [PEP 735](https://peps.python.org/pep-0735/)):**
  Non-published test, lint, type-checking, and refactoring tools (`dev`, `test`, `lint`).
- **Libraries vs. applications:**
  - *Reusable libraries:* Declare lower bounds (`>=`) and only genuine known upper incompatibilities
    in `[project.dependencies]` so downstream applications can resolve shared graphs.
  - *Applications and services:* Pin reproducible environments via the project's lockfile (`uv.lock`,
    `poetry.lock`, or pinned `requirements*.txt` constraints).
- **Lockfile integrity:** Always update lockfiles using the project's package manager ([`uv lock`](https://docs.astral.sh/uv/concepts/projects/layout/),
  `poetry lock`, `pip-compile`). You MUST NOT hand-edit generated lockfiles or upgrade unrelated
  packages as incidental cleanup during a scoped task.

## Toolchain Candidate Defaults and Improvement Rules

- **Unconstrained new projects:** Evaluate [`uv`](https://docs.astral.sh/uv/) (environment and package
  management), [`Ruff`](https://docs.astral.sh/ruff/) (linting and formatting),
  [`pytest`](https://docs.pytest.org/) (testing), and one maintained static type checker
  ([`mypy`](https://mypy.readthedocs.io/) or [`pyright`](https://microsoft.github.io/pyright/)) as
  candidate defaults. Verify compatibility with the target environment rather than treating them as
  hardcoded mandates.
- **Existing projects:** Respect the repository's established package manager and workflow (e.g.,
  `requirements-dev.txt` constraints vs. `uv.lock`). When existing tooling has a material gap (such as
  missing bugbear rules, unchecked type annotations, or broken lockfile workflows), recommend the
  improvement and execute it if tooling changes are within task scope.

## Semantic Equivalence Checks for Replacements

When replacing a custom implementation or migrating between libraries (e.g., custom parser to
`tomllib`/`pydantic`, `requests` to `httpx`, `os.path` to `pathlib`), explicitly verify and test
these semantic boundaries before removing the old code:

1. **Type coercion and truthiness:** Check whether strings like `"false"`, `"0"`, or `"no"` are
   coerced or rejected, and whether `bool` is accepted as an `int` (`isinstance(True, int)` is `True`
   in Python).
2. **Numeric precision and rounding:** Ensure `Decimal` vs. `float` precision and rounding modes
   (`ROUND_HALF_EVEN` vs. `ROUND_HALF_UP`) remain exact.
3. **Default values and missing keys:** Check `None` vs. omitted-key behavior and mutable default
   isolation.
4. **Exception types and hierarchy:** Catch library-specific exceptions at the boundary and raise the
   caller-expected domain exception (`raise ConfigError(...) from exc`) when callers catch specific
   types.
5. **Ordering and duplicate keys:** Verify whether insertion order or duplicate-key rejection changes.
6. **Timeouts, retries, and resource cleanup:** Confirm default timeouts (explicit vs. infinite),
   connection/file closing on error, and context-manager semantics match or improve safely.
