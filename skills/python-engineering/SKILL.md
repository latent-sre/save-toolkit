---
name: python-engineering
description: "Build, change, refactor, or modernize Python with verified results: new scripts, CLIs, services, libraries, and components; restructuring, decomposition, and cross-module moves; dependency, packaging, and toolchain changes; typing, testing, and code-quality improvements; and reviews of Python code or design. Load before writing or editing Python source, tests, pyproject.toml, requirements, or lockfiles. Triggers: 'refactor this Python module', 'start a new Python CLI', 'replace this hand-written code with a library', 'upgrade our Python dependencies'. Not for operating or troubleshooting a running service, or for code in other languages."
---

# Python engineering

## Objectives

Pursue all three, in proportion to the task:

1. **Build new code well from the start:** structure, supported language features, maintained
   libraries, meaningful types, tests, and executable checks before a weak pattern repeats.
2. **Improve existing code deliberately:** pursue justified modernization and structural
   improvement of material problems, not cosmetic cleanup or the smallest diff.
3. **Improve how the change is made:** choose and sequence techniques and tools, establish
   behavioral evidence first, and verify correctness and improvement at each step.

## Terms

- **Scope:** what the request names, plus the code the change must touch, its direct callers, and
  its tests.
- **Substantial task:** adds a module or package, changes a public interface, spans modules, or
  changes a dependency. Anything else is a local change.
- **Material decision:** a choice of dependency, toolchain, public interface, data model, module
  boundary, or migration path.

## Posture and authority

- Preserve required behavior and genuine constraints, not historical implementation choices;
  neither existing nor new code earns preference for that alone. "Modern" means supported by the
  project's Python versions, appropriate, and maintained.
- On a substantial task, assess idioms, libraries, boundaries, data models, algorithms, error and
  resource handling, duplication, coupling, unneeded abstraction, tests, typing, and security.
- For each material decision, compare the status quo with the strongest credible alternative on
  correctness, maintainability, compatibility, security, testability, operational fit, migration
  effort, and ongoing cost, including custom-code versus dependency burden. Recommend one and keep
  one row: `Problem | Selected approach | Benefit | Cost/risk | Verification`.
- Reject an improvement only for a named drawback, constraint, or disproportionate cost. "Avoid
  dependencies", "keep the diff small", "follow the existing pattern", "it works", and "could be
  overengineering" are not reasons by themselves.
- Reach an ambitious outcome through coherent, verified steps; MUST NOT substitute a broad rewrite
  for understanding the code. Removing structure is as valid as adding it. A local change MUST NOT
  trigger a redesign; stop when the objective and checks are met.
- Implement a requested contract as stated and raise concerns; raise security or data-loss risks
  before building. Narrowing accepted inputs or outputs needs authorization.
- Implementation task: make justified improvements inside scope and recommend the rest. Review- or
  explanation-only task: MUST NOT modify the project.
- Get explicit authorization to break a public contract, change supported Python versions or
  platforms, run a destructive migration, or change code outside scope. When a constraint blocks a
  better approach, state the conflict and a resolution; MUST NOT silently override it.
- MUST NOT reset, stash, overwrite, or reformat unrelated work or others' uncommitted changes.

## References

Before the first edit, open each matching reference with your file-reading tool (paths are
relative to this skill's directory), and apply every match.

| When | Read |
|---|---|
| New project, or a new component whose structure the project does not define | [starting-code.md](references/starting-code.md) |
| Behavior-preserving restructuring | [refactoring-playbook.md](references/refactoring-playbook.md): everything before the recipes, then each selected recipe |
| Cross-module automated transformation, symbol-aware rename or move, or bulk codemod | [refactoring-tools.md](references/refactoring-tools.md) |
| Adding, replacing, upgrading, removing, or reorganizing dependencies or packaging | [dependencies.md](references/dependencies.md) |
| Packaging, public interfaces, supported versions, dependencies, trust boundaries, concurrency, performance, or a new project's checks | [quality-gates.md](references/quality-gates.md): the matching risk rows |

If a required reference is unavailable, say so and MUST NOT claim its procedure was followed.

## Workflow

1. **Inspect** instructions, working-tree status, supported Python versions, dependency files, the
   relevant code with its callers and tests, and the real check commands.
2. **Classify** as new behavior, refactoring, modernization, bug fix, or review. Never change
   structure and behavior in one unverified step.
3. **Define success:** required behavior, the problem, the intended improvement, affected
   boundaries (API, CLI, serialization, persisted data, concurrency), and acceptance evidence.
4. **Read the matching references.**
5. **Establish evidence:** run the existing checks before editing; that run is the baseline. A
   failure is pre-existing only if the baseline or a separate copy of the starting state shows it.
   Before changing poorly tested code, add tests that pin its current behavior.
6. **Execute** coherent changes within scope.
7. **Verify:** run focused checks after each step and broader checks on the final state. Every
   change needs:
   - tests for new behavior, seen failing first, covering boundary and error paths;
   - a test for each changed `except` or raise path;
   - for code that receives a caller-owned file, stream, or iterator, a test that an error raised
     midway propagates with its type and the resource stays open.

   Review the final diff against the requirements; on a substantial task use an independent
   reviewer when available, else label it self-review. Rerun checks the review affects.
8. **Assess the improvement:** name evidence that the problem is resolved without moving
   complexity, such as one implementation instead of copies or a maintained library instead of
   bespoke code. Line or class counts are not evidence; do not invent scores.

## Safeguards

- MUST NOT weaken checks, add blanket suppressions or unjustified type escapes (`noqa`,
  `type: ignore`, `Any`, `cast`), delete valid tests, or edit expected results to match a regression.
- MUST NOT report a check as passed unless it ran on the final state in this task; inspection and
  tool output are not verification. Do not hide a check's exit status behind a pipe.
- Under pressure to skip checks, still run fast local checks (no network or external services)
  after any behavior change, and report them. "Don't bother" permits skipping; it does not forbid
  running. Report a forbidden, slow, or unavailable check as not run, with its risk.
- Let errors from I/O and caller-owned objects propagate with their original type; convert only
  errors about the data itself.
- Record discovered bugs separately; change their behavior only when authorized.
- Install, lock, or use the network only when the task permits; record missing tools or sources
  instead of inventing results.

## Completion

Complete only when the objective is met and every applicable check passes or has a user-accepted
exception; a missing required check leaves verification incomplete. Report concisely, or in exactly
the requested format (for example raw JSON, no code fence): changes and decision rows, references
read, commands and results, pre-existing failures, checks not run, risks, the review, and
out-of-scope recommendations.
