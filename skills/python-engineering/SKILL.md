---
name: python-engineering
description: "Build, change, refactor, or modernize Python with verified results: new scripts, CLIs, services, libraries, and components; restructuring, decomposition, and cross-module moves; dependency, packaging, and toolchain changes; typing, testing, and code-quality improvements; reviews of Python code or design; and explanations of what Python code does. Load before writing or editing Python source, tests, pyproject.toml, requirements, or lockfiles. Triggers: 'refactor this Python module', 'start a new Python CLI', 'replace this hand-written code with a library', 'upgrade our Python dependencies'. Not for operating or troubleshooting a running service, or for code in other languages."
---

# Python engineering

## Objectives

Pursue all three on every task, in proportion to its size:

1. **Build new code well from the start.** Set structure, supported language features, maintained
   libraries, meaningful types, tests, and executable quality checks before a weak pattern repeats.
2. **Improve existing code deliberately.** Find the material problems, then pursue justified
   modernization and structural improvement, not cosmetic cleanup or the smallest possible diff.
3. **Improve how the change is made.** Select and sequence techniques and tools, establish
   behavioral evidence first, and verify correctness and improvement at each step.

## Terms

- **Scope:** the files, symbols, and behaviors the request names, plus the code the change must
  touch, its direct callers, and its tests.
- **Substantial task:** adds a module or package, changes a public interface, spans more than one
  module, or adds, removes, replaces, or upgrades a dependency. Any other task is a local change.
- **Material decision:** a choice of dependency, toolchain, public interface, data model, module
  boundary, or migration path.

## Posture

- Preserve required behavior and genuine constraints, not historical implementation choices.
  Existing code earns no preference for existing; a new approach earns none for being new.
  "Modern" means supported by the project's Python versions, appropriate, and maintained.
- On a substantial task, assess language features and idioms, maintained libraries, module
  boundaries, interfaces and data models, algorithms, resource and error handling, duplication,
  coupling, obsolete code, unneeded abstraction, tests, typing, security, and executable checks.
- For each material decision, compare the status quo with the strongest credible alternative on
  correctness, maintainability, compatibility, security, testability, operational fit, migration
  effort, and ongoing cost, weighing custom-code burden against dependency burden. Recommend one
  and keep one row: `Problem | Selected approach | Benefit | Cost/risk | Verification`. No design
  document for routine decisions.
- Reject an improvement only for a named drawback, constraint, or disproportionate cost. "Avoid
  dependencies", "keep the diff small", "follow the existing pattern", "it works", and "could be
  overengineering" are not reasons by themselves.
- Aim the outcome high and execute in coherent, verified steps. MUST NOT replace understanding the
  existing code with a broad rewrite. Removing structure is as valid a result as adding it.
- Implement a requested contract as stated and raise concerns about it. If it creates a security or
  data-loss risk, raise that before building and follow the owner's decision. Rejecting inputs or
  dropping outputs the contract allows needs authorization.
- A local change MUST NOT trigger a redesign. Stop when the objective and applicable checks are
  met; do not keep redesigning because more is possible.

## Authority

- Implementation task: carry out justified improvements inside scope; recommend the rest.
  Review-only or explanation-only task: recommend or explain; MUST NOT modify the project.
- Obtain explicit authorization before breaking a public contract, changing supported Python
  versions or platforms, running a destructive data migration, or changing code outside scope
  across the repository.
- When an explicit constraint blocks a better approach, state the conflict and a recommended
  resolution; MUST NOT silently override the constraint.
- MUST NOT reset, stash, overwrite, or reformat unrelated work or others' uncommitted changes.

## Required references

Before the first edit, open every matching reference with your file-reading tool; paths are
relative to this skill's directory. Apply every matching route. Every task matches the last row.

| When | Read |
|---|---|
| New project, or a new component whose structure the project does not already define | [starting-code.md](references/starting-code.md) |
| Any behavior-preserving restructuring | [refactoring-playbook.md](references/refactoring-playbook.md): everything before the recipes, then the complete recipe for each technique selected |
| Cross-module automated transformation, symbol-aware rename or move, or a bulk codemod | [refactoring-tools.md](references/refactoring-tools.md) |
| Adding, replacing, upgrading, removing, or reorganizing dependencies or packaging | [dependencies.md](references/dependencies.md) |
| Selecting verification | [quality-gates.md](references/quality-gates.md): the whole file, then run every matching risk row |

If a required reference is unavailable, say so and MUST NOT claim its procedure was followed.

## Workflow

1. **Inspect.** Read applicable instructions, the working-tree status, supported Python versions,
   dependency and lock files, the relevant code with its callers and tests, and the repository's
   real check commands.
2. **Classify.** New behavior, behavior-preserving refactoring, modernization, bug fix, or review.
   Split mixed work into separately verified steps; never change structure and behavior in the
   same unverified step.
3. **Define success.** Required behavior, the problem being solved, the intended improvement,
   affected boundaries (public API, CLI, serialization, persisted data, concurrency), and the
   evidence that will show acceptance.
4. **Consult the references** in the table above.
5. **Establish evidence.** Run the relevant existing checks before editing; that run is the
   baseline. A failure is pre-existing only if the baseline shows it or a separate copy of the
   starting state reproduces it. Add missing behavioral coverage before changing existing behavior
   or structure.
6. **Execute** coherent changes within scope, using suitable libraries, techniques, and tools.
7. **Verify.** Run focused checks after each step and the relevant broader checks on the final
   state. Review the final diff against the requirements and likely failure modes, including
   unintended edits, leftovers, and new suppressions. On a substantial task, use an independent
   reviewer when one is available; otherwise label the review as self-review. Rerun the checks
   that review-driven edits affect.
8. **Assess the improvement.** Name the evidence that the original problem is resolved and that
   complexity did not just move. Examples: duplicated behavior now has one implementation; a
   responsibility has a testable boundary; a maintained library replaced bespoke code; indirection
   or an import cycle is gone; a resource gain is measured. Fewer lines, more files, more classes,
   or smaller functions are not evidence by themselves. Do not invent scores.

## Safeguards

- MUST NOT weaken a check, add blanket suppressions or unjustified type escapes (`noqa`,
  `type: ignore`, `Any`, `cast`), delete a valid test, or edit an expected result to match a
  regression.
- MUST NOT report a check as passed unless it ran against the final state in this task. Static
  inspection is not runtime verification; a tool-generated change is not proof of correctness.
  Keep each check's exit status and summary visible: run it unpiped and read its status (`$?` in
  POSIX shells, `$LASTEXITCODE` in PowerShell); if you must pipe in a POSIX shell, run
  `set -o pipefail` first. Never let `| tail`, `| grep`, or `|| true` hide the status.
- Under pressure to skip checks, still run fast local checks (no network, no external services, no
  writes outside the working tree and temporary directories) after any behavior change, and report
  the result. "No need" or
  "don't bother" permits skipping; it does not forbid running. If the user forbids a check, or it is
  slow or unavailable, report it as not run, with its risk.
- Record discovered bugs separately; change their behavior only when the task authorizes it.
- Install packages, update lockfiles, or use the network only when the task permits. When a
  required tool or source is unavailable, record the gap instead of inventing results.

## Completion

The task is complete only when the objective is met and every applicable check passes or has an
exception the user explicitly accepted. An unavailable required check leaves verification
incomplete; say which check and why.

Report concisely, unless the request specifies an output format; then return exactly that format,
for example raw JSON with no code fence:

- Material changes and their decision rows.
- References read, and the exact commands run with their scope and results.
- Pre-existing failures with their evidence, checks not run, remaining risks, the review performed
  (independent or self), and recommended improvements outside scope.
