---
name: python-engineering
description: >-
  Implement, modify, refactor, modernize, and verify Python code, dependencies, packaging, and
  quality gates. Use when creating Python scripts, CLIs, libraries, or services; restructuring or
  modernizing legacy Python modules; selecting or replacing packages; or establishing pytest, Ruff,
  and type-checking verification. Not for live incident bridge coordination without code changes
  (incident-investigation) or non-Python language work (go-craft, frontend-craft). Triggers:
  "write or refactor this Python code", "modernize this Python module", "replace this custom Python
  implementation with a library", "add Python tests and quality gates".
argument-hint: "[Python module, feature, refactoring, dependency, or verification task]"
---

# Python Engineering

## Primary Objectives

Every task MUST enforce three equally binding responsibilities:

1. **Build new code well from the start.** Establish fitting module structure, supported Python
   features, maintained libraries, explicit type boundaries, behavioral tests, and executable
   quality checks before weak patterns spread.
2. **Improve existing code deliberately.** Identify material structural or behavioral weaknesses,
   evaluate stronger alternatives, and execute justified modernization and design improvements
   rather than cosmetic cleanup or minimal-diff avoidance.
3. **Improve the refactoring process itself.** Sequence behavior-preserving transformations, choose
   semantic tools, establish baseline and characterization evidence before restructuring, and verify
   both contract preservation and structural improvement.

## Engineering Posture and Decision Rules

- **Assess better approaches actively.** For substantial tasks, evaluate supported Python features
   and idioms, maintained libraries, module boundaries and data models, algorithms and resource/error
   handling, duplication and coupling, dead code or unnecessary abstractions, and executable typing,
   testing, and security checks.
- **No automatic preference for status quo or novelty.** Compare the current code against the
  strongest credible alternative across correctness, maintainability, compatibility, security,
  testability, operational fit, migration effort, and ongoing cost. Weigh custom-code maintenance
  against dependency cost, and existing complexity against proposed complexity.
- **Reject unsupported conservatism.** Rationales such as *"avoid dependencies"*, *"keep the diff
  small"*, *"follow the existing pattern"*, *"the current code works"*, or *"that could be
  overengineering"* MUST NOT block an improvement without a concrete constraint, defect risk, or
  disproportionate cost.
- **Define "modern" by fitness.** Use supported, maintainable features valid for the project's
  Python floor—not experimental or fashionable constructs. Apply ambition to the outcome and
  incremental, verified steps to execution.
- **Recommend the strongest justified solution.** Do not present unequal options as equally valid.
  For consequential design or dependency decisions, record:
  `Problem | Selected approach | Benefit | Cost/risk | Verification`

## Mandatory Reference Routing

Route based on **what `A. Inspect` reveals in the code and `pyproject.toml`**, not only the user's
prompt wording. Every task MUST consult [quality-gates.md](references/quality-gates.md) (applicable
risk-to-check rows) alongside its task-specific reference(s); MUST NOT load unrelated references.

| Trigger condition (from prompt or `A. Inspect`) | Required action |
|---|---|
| Creating a new project, a new module, or implementing new code in a stub module where layout/packaging is decided | Read [starting-code.md](references/starting-code.md) |
| Refactoring, cleaning up, decomposing, splitting modules, moving symbols across modules, or extending existing code with structural smells (long functions, mixed responsibilities, duplication, mutable globals, pass-through class hierarchies, or ad-hoc parsers), or reviewing a refactoring proposal | Read [refactoring-playbook.md](references/refactoring-playbook.md) (decision table + full applicable recipes) |
| Moving or renaming symbols across modules, splitting modules, updating package exports, or applying bulk/automated transformations | Read [refactoring-tools.md](references/refactoring-tools.md) alongside [refactoring-playbook.md](references/refactoring-playbook.md) |
| Adding, replacing, or upgrading packages, or when `A. Inspect` finds `pyproject.toml` libraries or a custom parser/validator/client that stdlib (`tomllib`, etc.) or an installed package (`pydantic`, etc.) should replace | Read [dependencies.md](references/dependencies.md) |
| Selecting or running verification checks for any task, or configuring/improving project quality gates | Read [quality-gates.md](references/quality-gates.md) (applicable risk-to-check entries) |

If a required reference is unavailable, disclose the gap and MUST NOT claim its procedures were
followed.

## Universal Execution Workflow

Execute this sequence in proportion to the task (trivial edits MUST NOT trigger repo-wide redesigns):

A. **Inspect.** Read applicable instructions, working-tree changes, supported Python versions,
   project layout, dependency config, target code, callers, exports, dynamic lookups, tests, and
   CI/quality commands. MUST NOT reset, overwrite, or reformat unrelated user changes.
B. **Classify.** Distinguish new behavior, behavior-preserving refactoring, modernization, and
   review-only work. Split mixed work into sequenced, independently verifiable steps.
C. **Define success.** Identify required observable contracts, the concrete problem, intended
   improvement, affected boundaries, and acceptance evidence.
D. **Consult references.** Load all triggered routes from the table above.
E. **Establish evidence.** Capture baseline check results and add failing behavioral tests (new
   behavior) or passing characterization tests (undertested existing code) before changing code.
F. **Execute.** Perform coherent changes within authorized scope using appropriate libraries,
   techniques, and semantic tools.
G. **Verify.** Run focused checks during iteration, broader checks on the final state, and an
   independent or explicitly labeled self-review of the diff, rerunning checks after any fix.
H. **Assess improvement.** Confirm with concrete evidence that the problem improved—such as one
   authoritative implementation for duplicated behavior, a testable boundary, replaced bespoke
   plumbing, removed indirection or cycles, narrower invalid-state types, or measured resource
   gains. Line, file, or class counts and invented scores are not standalone evidence. Stop once the
   objective and gates are satisfied.

## Verification Integrity, Authority, and Completion

- **Verification integrity.** MUST NOT weaken checks, add blanket `# noqa` or unjustified
  `# type: ignore` suppressions, delete valid tests, alter expected test results to match a
  regression, treat static inspection as runtime verification, or claim unexecuted/stale checks
  passed.
- **Scope and authority.** Execute justified internal improvements within implementation scope;
  recommend out-of-scope improvements explicitly. For review-only tasks, recommend without editing.
  Escalate breaking public contracts, platform floor changes, destructive migrations, or unrelated
  repo-wide changes. If an explicit constraint blocks a better approach, surface the conflict and
  recommend a resolution without silently overriding it.
- **Completion and reporting.** Require applicable checks to pass or an explicit exception;
  unavailable required checks leave verification incomplete. Report concisely:
  - Material changes and consequential engineering decisions (`Problem | Selected approach | Benefit | Cost/risk | Verification`).
  - Exact checks executed, their scope, and results.
  - Pre-existing failures, unexecuted checks, and remaining risks.
