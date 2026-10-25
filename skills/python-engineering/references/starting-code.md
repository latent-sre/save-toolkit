# Starting code

Use this procedure for a new project or for a new component whose structure the project does not
already define. Inside an existing project, its layout, tooling, and conventions are the
starting point; use the steps below for the parts it leaves open.

## Contents

- 1. Classify the deliverable
- 2. Establish the runtime
- 3. Choose layout and packaging
- 4. Map the work
- 5. Reuse before building
- 6. Set type boundaries
- 7. Write acceptance tests first
- 8. Build one vertical slice
- 9. Persist durable decisions
- Structure rules
- Re-verify

## 1. Classify the deliverable

| Deliverable | Layout | Entry point | Packaging | Tests |
|---|---|---|---|---|
| Standalone script | One file | `main(argv: list[str] \| None = None) -> int` called under `if __name__ == "__main__":` | None. Declare third-party needs with inline script metadata only if the target runtime honors it | Import the file and call `main` or its functions |
| CLI | Package with a `cli` module | `[project.scripts]` | `pyproject.toml` | Call `main(argv)` in process; one subprocess test of the installed entry point |
| Service | Package; I/O adapters at the edges | Process entry (`__main__`, ASGI/WSGI app factory, worker) | `pyproject.toml` plus the deployment's artifact | Core logic in process; boundaries through contract or integration tests |
| Reusable library | `src/` layout | Public API exported from the package `__init__` with `__all__` | `pyproject.toml` with compatible version ranges, `py.typed` when typed | Test the installed package, not the source tree |
| Component in an existing project | The project's layout | The project's mechanism | The project's | The project's runner and conventions |

Record the classification. MUST NOT impose package scaffolding on a standalone script, or script
habits (logic under `if __name__`, module-level state) on a package.

## 2. Establish the runtime

- Determine the supported Python versions from the deployment target, `requires-python`, the CI
  matrix, and the container or host image. Check the
  [Python version status page](https://devguide.python.org/versions/) before choosing a minimum;
  MUST NOT target an end-of-life version without an explicit constraint. Offline, use the
  deployment's constraints and the local interpreters, and record the support status as
  unverified.
- Use language and standard-library features available in the minimum supported version.
- Record where the code runs (bare interpreter, virtual environment, container, serverless) and
  what that permits: installs, native extensions, network, writable filesystem.

## 3. Choose layout and packaging

- Choose the smallest layout that serves the deliverable. A single module beats a package of
  one-function modules.
- When project-level packaging or tool configuration is needed, use `pyproject.toml`: `[project]`
  for metadata, `requires-python`, and runtime dependencies; `[build-system]` for the build backend;
  `[dependency-groups]` for development tools; `[tool.<name>]` for tool settings.
- Libraries: prefer the `src/` layout so tests run against the installed package and not files that
  happen to sit on `sys.path`.
- Never put secrets, host paths, or environment-specific values in source; read configuration at
  the entry point and pass values inward.

## 4. Map the work

Before writing code, list:

- Entry points and their contracts: arguments, exit codes, stdout versus stderr, return values,
  raised exceptions.
- Core behavior that can be pure and deterministic.
- External interactions: files, network, databases, subprocesses, clock, randomness, environment.
- Configuration sources and precedence.
- Testing boundaries: where a fake or fixture replaces a real dependency. Inject a dependency only
  where a test or a real variation needs the seam.

## 5. Reuse before building

- Search the project for existing modules, helpers, and dependencies that already provide the
  capability. Extend them instead of creating a parallel implementation.
- Before writing custom code, beyond what the standard library or a few lines provide, for a
  published format or specification, validation, retries and backoff, time zones, a CLI framework,
  serialization, or concurrency primitives, evaluate maintained libraries under the dependency
  route and record the decision row.

## 6. Set type boundaries

- Annotate every public function, method, and class attribute, and every function at an external
  boundary.
- Parse external data (files, HTTP, environment, CLI input) into typed structures at the boundary,
  such as dataclasses, `TypedDict`, enums, or the validation library already in use. Pass the
  typed values inward rather than raw dictionaries.
- Use `Literal` or `Enum` for closed sets. Make invalid states unrepresentable when that costs
  little.

## 7. Write acceptance tests first

1. Write behavioral tests for each required behavior, boundary value, and error path.
2. Run them before implementing. Each MUST fail for the intended missing behavior, such as an
   assertion or a missing attribute on the feature. An import error, fixture failure, or
   collection error means the test setup is broken: fix the setup, then rerun.
3. Implement until they pass. Do not edit an assertion to fit the implementation unless the
   requirement itself was misread; record that correction.

## 8. Build one vertical slice

- Implement one end-to-end behavior through the real entry point, with lint, format, type check,
  and tests passing.
- Review that slice before repeating its pattern: module boundaries, naming, error handling, test
  seams, and configuration flow. Fix the pattern now; copies multiply its defects.

## 9. Persist durable decisions

- Put tool settings in `pyproject.toml` (or the project's existing config files), and check commands
  in CI when CI is in scope.
- Add durable rules (supported versions, how to run checks, deployment constraints) to the README
  or the repository's existing instruction files. Do not write a design document for routine
  decisions.

## Structure rules

- MUST NOT add layers, factories, repositories, service classes, inheritance hierarchies, or a
  dependency-injection framework by default. Add structure when it resolves a concrete
  responsibility, testing, reuse, or change boundary, and name that boundary.
- MUST NOT start with knowingly poor structure that will need refactoring: a god module, mutable
  module-level state, import-time side effects, logic inside the `__main__` block, or I/O tangled
  into core rules.
- MUST NOT design speculative extension points for requirements nobody has stated.
- Defaults for new code:
  - Catch specific exceptions and chain them with `raise ... from`.
  - Manage resources with context managers.
  - Use `pathlib` for paths.
  - Use timezone-aware datetimes.
  - Call `subprocess` with argument lists and no `shell=True` on untrusted input.
  - Use `logging` for diagnostics, and keep stdout for program output.

## Re-verify

Check these when the packaging or layout guidance here disagrees with the installed tools.

- [Writing your pyproject.toml](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)
- [pyproject.toml specification](https://packaging.python.org/en/latest/specifications/pyproject-toml/)
- [Dependency groups specification](https://packaging.python.org/en/latest/specifications/dependency-groups/)
- [Inline script metadata specification](https://packaging.python.org/en/latest/specifications/inline-script-metadata/)
- [pytest good integration practices](https://docs.pytest.org/en/stable/explanation/goodpractices.html) (src layout)
