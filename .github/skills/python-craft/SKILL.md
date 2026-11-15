---
name: python-craft
description: >-
  Build, implement, refactor, rewrite, and modernize production-quality Python: services, CLIs,
  libraries, scripts, tests, packaging, and tooling. Use before writing or changing Python,
  choosing, upgrading, or replacing Python dependencies, restructuring or modernizing a legacy
  module, or setting up uv, pyproject.toml, Ruff, pytest, and type checking; also for explaining
  or designing Python. Triggers: 'write this in Python', 'refactor this Python', 'modernize this
  module', 'replace this custom code with a library'. Not for operating a running service or
  changing another language.
argument-hint: "[Python code, file, or task]"
---

# Python craft

Build production-quality Python from the first commit, and substantially improve existing Python
when the task calls for it. Explanation, design, and review requests end at that output.

## Authority and priorities

- **Own routine engineering decisions** inside the authorized objective. Select and implement the
  strongest justified solution; do not hand the user a menu of ordinary technical choices.
- **Optimize for** correctness, maintainability, capability, operational reliability, performance
  where it matters, and total engineering cost.
- **Dependencies and architectural change are ordinary options from the start.** Apply no
  standard-library-first, dependency-minimizing, minimal-diff, or preserve-existing-design default.
  The standard library, existing dependencies, and new packages compete on merit.
- **Complexity must buy concrete value.** Never reject a stronger design only because it adds
  techniques, modules, or dependencies, and never add them for show. The result must stay
  understandable and supportable.
- **The objective sets scope; the existing design does not.** Improve whatever architecture the
  objective needs and leave unrelated code alone. Existing code is evidence about requirements and
  behavior, not a boundary on its replacement. Respect explicit project constraints (runtime,
  deployment, licensing, compatibility, stated policy); habits and accidental legacy conventions
  are not constraints.
- **Surface only consequential uncertainty** the authorization does not settle: requirements,
  external compatibility, irreversible effects. State other assumptions and keep working on
  whatever does not depend on the answer.

## Baseline

- **Python 3.14 is the floor** for new projects (`requires-python = ">=3.14"`) and the
  modernization target for existing ones. Choose a higher floor when project requirements justify
  it and the authorized compatibility scope allows. Never silently raise the floor or add support
  for older Python.
- **Write for the declared floor**, using the modern syntax and APIs it supports. The development
  interpreter is a separate choice: running a newer Python does not authorize features the floor
  lacks.
- **uv and `pyproject.toml`** for maintained projects: environments, dependencies, locking, and
  project commands go through uv. Metadata and tool settings live in TOML where the tool supports
  it; keep a tool's native file when it requires one.
- **Dependencies in their own fields:** runtime in `project.dependencies`, user-facing extras in
  `project.optional-dependencies`, development tools in `[dependency-groups]`. Change them with
  `uv add` and `uv remove`. Commit `uv.lock`; uv generates it.
- **Current dependencies:** add packages at their current stable release. Modernization upgrades
  existing dependencies to current major versions, migrates off deprecated APIs, and replaces
  unmaintained packages; an old pin needs a stated reason.
- **Locked verification:** `uv sync --locked` and `uv run --locked …` in CI and reproducible
  checks. `--frozen` skips the check that metadata and lockfile agree; never substitute it.
- **Distributable packages** declare a build backend; verify the built artifact when packaging
  changes. A library's lockfile governs its own development; its published metadata carries
  supported ranges, never the lock's exact transitive pins.
- **Quality tools:** Ruff for linting and formatting, pytest, and one maintained type checker, all
  targeting the floor. Strict typing for new or substantially rewritten code; a deliberate,
  recorded boundary around existing untyped code.
- **When a project conflicts with this baseline** (older runtime, stale dependencies, another
  package manager, legacy build), name the conflict and a concrete migration path. Neither keep an obsolete foundation
  silently nor force a repository-wide migration into a narrow task.

## Workflow

1. **Establish the objective and constraints.** Size the response: a narrow repair gets a focused
   change, a regression test, and focused verification; a design problem gets a design answer.
2. **Design before editing.** Name the problem and the intended improvement. Evaluate suitable
   libraries now, not after a bespoke version becomes difficult. For existing code choose focused
   refactoring, staged replacement, or a rewrite on the merits; a rewrite does not require
   exhausting small patches first.
3. **Establish what must hold.** Externally relied-upon contracts and important invariants come
   from documentation, callers, tests, and observed behavior. Separate required behavior from
   implementation accident and confirmed defects. Before substantial replacement, cover
   consequential unprotected behavior with characterization or regression tests.
4. **Implement completely.** Integrate each chosen library into one coherent design and remove the
   custom machinery it supersedes. Update callers, imports, configuration, dependencies,
   documentation, and tests; delete dead paths. Keep a transitional adapter only for a real
   compatibility need, with a stated removal condition. Preserve required behavior unless changing
   it is authorized; make intentional changes to interfaces, data formats, errors, or operational
   behavior explicit and supply the migration.
5. **Verify in proportion to risk, then report.**

## Verification and completion

- Run focused tests while developing, plus lint, format, and type checks on what changed. Add
  integration, property-based, concurrency, packaging, or performance checks when each answers a
  named risk.
- Keep behavioral coverage when internals move: re-express tests coupled to obsolete internals so
  they still protect the behavior. Never weaken an assertion or delete a failing test to make a
  change pass.
- When compatibility is affected, test the minimum supported Python, and newer versions or
  deployment targets when the change warrants. A passing development environment does not
  establish the declared range.
- Run broader suites when a required gate or the affected dependency surface calls for them. Reuse
  still-valid evidence; repeat a check only when later edits invalidated it or a concrete risk
  remains unresolved. Stop when required gates and material risks are covered.
- Back performance claims with representative measurements.
- Report briefly: what changed, why the design is better, the checks actually run with their
  results, and material limitations. Never report a check that did not run, or present an
  unfinished migration as complete.

## References

Load only what the task triggers; the policies above hold without them.

| When | Read |
|---|---|
| Choosing structure, data models, a library, a concurrency model, or failure behavior | [Design and dependencies](references/design.md) |
| Restructuring, replacing, or rewriting existing code; migrating callers, data, or dependencies | [Refactoring and migration](references/refactoring.md) |
| Changing project setup, packaging, CI, or tool configuration; adding or upgrading dependencies; choosing checks for a named risk | [Tooling and verification](references/tooling.md) |
