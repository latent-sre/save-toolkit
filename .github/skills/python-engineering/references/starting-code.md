# Starting New Python Code and Components

## Contents

- Deliverable Classification and Layout Selection
- Step-by-Step Starting Procedure
- Type and Boundary Design Rules
- Structural Discipline and Anti-Bloat Safeguards
- Configuration and Persistence Standards

## Deliverable Classification and Layout Selection

Before writing implementation code, classify the deliverable and select the smallest layout that
supports its execution, import, and testing boundaries:

| Deliverable type | Required layout decision | Packaging rule |
|---|---|---|
| Standalone script | Single `<name>.py` file with a `main(argv: Sequence[str] | None = None) -> int` entry point and `if __name__ == "__main__":` guard | MUST NOT force package directories, `src/` scaffolding, or build backends onto a single-file script unless distribution or multi-module growth is required. Optionally use inline script metadata ([PEP 723](https://peps.python.org/pep-0723/)) when isolated script dependencies are needed |
| CLI application | Importable package (`<pkg>/` or `src/<pkg>/`) separating argument parsing/IO from core domain logic, plus `[project.scripts]` entry point | Configure `[build-system]` and `[project]` in `pyproject.toml` ([PyPA pyproject.toml](https://packaging.python.org/en/latest/specifications/pyproject-toml/)) |
| Service or worker | Package separating transport/framework wiring, configuration loading, and pure domain/policy modules | Manage runtime vs. development dependencies and lockfiles for reproducible deployment ([dependencies.md](dependencies.md)) |
| Reusable library | `src/<pkg>/` layout (prevents accidental uninstalled local imports during testing), explicit `__all__`, and `py.typed` marker ([PEP 561](https://peps.python.org/pep-0561/)) | Define compatibility ranges in `requires-python` and `[project.dependencies]` without pinning consumer applications |
| Component inside an existing project | Module or subpackage matching the repository's established package root, naming, and test layout | Reuse existing `pyproject.toml`, test runner, and lint/type configuration |

## Step-by-Step Starting Procedure

Execute these actions in order when creating a new project or substantial component:

1. **Establish runtime and environment constraints.** Confirm supported Python versions
   (`requires-python`, `.python-version`, CI matrix) and execution environment (virtualenv, `uv`,
   container, or bare interpreter).
2. **Inspect existing capabilities before creating new ones.** Search the repository and installed
   environment for existing modules, shared helpers, and declared packages. MUST NOT create
   duplicate utilities when a project module already owns that responsibility.
3. **Evaluate maintained libraries before coding substantial custom logic.** When the task involves
   non-trivial capabilities (such as schema validation, HTTP clients, retries, CLI parsing,
   date/time/timezone handling, or structured concurrency), consult [dependencies.md](dependencies.md)
   to compare maintained libraries and standard-library facilities against custom code cost.
4. **Define boundaries before implementation.** Identify:
   - Entry points (CLI, HTTP handler, public function/class API).
   - Core pure computation or domain policy (testable in memory without network or filesystem IO).
   - External interactions (files, databases, subprocesses, network, clock/randomness).
   - Configuration inputs and validation boundary.
5. **Define explicit type boundaries.** Annotate all public functions, methods, return types, and
   external data models (`dataclasses.dataclass(frozen=True, slots=True)`, `typing.TypedDict`,
   `typing.Protocol`, `enum.Enum`, or `pydantic.BaseModel` when validation/coercion is required).
   Validate untrusted external inputs at the boundary so internal functions operate on typed values.
6. **Write failing behavioral acceptance tests first.** Write tests targeting the required public
   behavior and error paths. Execute the test runner and confirm the new tests **fail for the
   intended missing behavior**—not due to `ImportError`, syntax errors, or broken test fixtures.
7. **Implement one end-to-end vertical slice.** Build one complete working path through the chosen
   boundary and run all applicable checks from [quality-gates.md](quality-gates.md) (tests, linter,
   formatter, type checker).
8. **Review the first slice before scaling.** Inspect the slice for leaking abstractions, awkward
   call signatures, hidden global state, or untestable IO coupling. Correct the structure before
   repeating the pattern across remaining features.
9. **Persist durable decisions.** Record supported Python version, dependency groups, linter/type
   settings, and test commands in `pyproject.toml` and existing repository documentation so future
   runs enforce the same standards automatically.

## Type and Boundary Design Rules

- **Prefer concrete data structures over untyped mappings.** Replace ad-hoc `dict[str, Any]`
  records crossing module boundaries with `@dataclass(slots=True)`, `NamedTuple`, `TypedDict`, or
  validated schema models.
- **Inject volatile dependencies explicitly.** Pass clocks (`Callable[[], float] = time.monotonic`),
  random generators, file paths/streams, or client interfaces as parameters with sensible defaults
  rather than hardcoding globals or requiring `unittest.mock.patch` on internal imports.
- **Keep import-time execution free of side effects.** Modules MUST NOT open network connections,
  mutate global state, read required environment variables without fallback, or perform filesystem
  writes at import time.

## Structural Discipline and Anti-Bloat Safeguards

- **Introduce structure only to solve a concrete boundary.** Create a separate module, class, or
  protocol only when it isolates a distinct responsibility, state lifecycle, IO boundary, or
  genuinely varying implementation.
- **Prohibited speculative scaffolding.** You MUST NOT automatically introduce:
  - `Abstract*` base classes, `I*` interfaces, or `Protocol` definitions when only one concrete
    implementation exists.
  - `*Factory`, `*Builder`, `*Manager`, `*Service`, or `*Repository` wrapper classes that merely
    forward calls without owning state or policy.
  - Deep subpackage hierarchies (`domain/`, `application/`, `infrastructure/`, `adapters/`) for
    small scripts, utilities, or bounded modules.
  - Third-party dependency-injection containers.
- **Never defer basic hygiene.** Starting simple means choosing a direct, flat design—not writing
  untyped, monolithic, or untested functions with the excuse that they can be refactored later.

## Configuration and Persistence Standards

When project-level configuration is in scope, consolidate settings in `pyproject.toml` ([PyPA
pyproject.toml](https://packaging.python.org/en/latest/specifications/pyproject-toml/)):

- Declare `[project]` metadata including `name`, `version`, `requires-python`, and runtime
  `dependencies`.
- Separate non-published development tooling under `[dependency-groups]` ([PEP 735](https://peps.python.org/pep-0735/))
  and user-installable extras under `[project.optional-dependencies]`.
- Configure `[tool.ruff]`, `[tool.mypy]` or `[tool.pyright]`, and `[tool.pytest.ini_options]` in
  `pyproject.toml` rather than scattering dotfile configs, unless the repository already standardizes
  on separate config files.
