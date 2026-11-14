---
name: python-craft
description: >-
  Build, refactor, modernize, or review Python: scripts, CLIs, services, libraries,
  tests, dependencies, packaging, and quality checks, including .py modules and pyproject.toml
  projects. Load before writing or editing any Python, choosing or replacing a Python library,
  or verifying a Python change. Not for live incident triage without code changes
  (incident-investigation) or other languages (go-craft, frontend-craft). Triggers: 'improve
  this Python', 'refactor this Python', 'modernize this module'.
argument-hint: "[Python code, file, or task]"
---

# Python craft

Three equal objectives: build new code well from the start, improve existing code deliberately,
and improve how refactoring is done. Preserve required behavior and genuine constraints, not
historical implementation choices. This skill adds no tools or authority.

## Judgment

- For material decisions, compare the current approach with the strongest credible alternative on
  correctness, clarity, maintainability, compatibility, security, testability, operational fit,
  migration effort, and recurring cost, weighing bespoke-code maintenance against dependency cost.
  Neither existing code nor novelty wins by default; recommend the best-supported option.
- "Avoid dependencies", "keep the diff small", "follow the existing pattern", "it already works",
  and "might be overengineering" reject nothing alone: name a concrete drawback, constraint, or
  disproportionate cost. New structure meets the same bar: name the responsibility it resolves.
- Make ordinary engineering decisions yourself, without redundant approval: libraries, internal
  interfaces, module boundaries, algorithms, tools. Ask only when missing information or authority
  changes required behavior, a supported external contract, data, live-system effects, or scope
  (such as breaking a public contract, swapping a framework or runtime, raising the Python floor,
  or a destructive migration); continue independent work meanwhile.
- Explicit constraints and unrelated user changes bind; never reset or reformat work you did not
  make. Surface a constraint that blocks a materially better approach rather than overriding it.
- Review, design, and explanation requests stay read-only unless changes are authorized; report
  valuable out-of-scope improvements without making them.

## Workflow

Scale each step to the task; none is a required report or approval stage. Trivial edits stay
trivial, and a broad rewrite never substitutes for understanding the code. Avoid redundant
questions, repeated research, duplicate checks, and delegation without distinct value.

1. **Inspect** instructions, working-tree changes, the Python floor and deployment targets, the code
   and its static and dynamic consumers, dependencies, tests, and the real check commands.
2. **Classify** the work as new behavior, behavior-preserving refactoring, modernization, defect
   repair, or review, keeping intentional behavior changes apart from structural steps.
3. **Define success**: required behavior, the actual problem, the intended improvement, affected
   boundaries, acceptance evidence. For a defect, establish cause and expected behavior and
   reproduce it; resolve uncertain requirements instead of guessing.
4. **Read every matching reference before that work, and no others**; if one is unavailable, say
   so and do not claim its procedures:
   - a new script, CLI, service, library, or substantial component; a dependency added, replaced,
     or upgraded; packaging; modernization; or touched code handling data types, errors, retries,
     async work, shared state, resources, or text encoding: [design and dependencies](references/design-and-dependencies.md)
   - restructuring, migration, deletion, or automated transformation: [refactoring](references/refactoring.md)
   - choosing checks or declaring any code change complete: [verification](references/verification.md)
5. **Establish evidence**: reuse checks that still match the code and environment; run a fresh
   baseline when needed to tell existing failures from regressions. Characterize poorly tested
   behavior before restructuring it. For new behavior and defect repair, first write a test that
   fails for the intended reason where practical; skip tests for trivial edits and tests that
   mirror the implementation.
6. **Implement** one complete path through its entrypoint, including failures and cleanup; review
   its boundaries before repeating the pattern; migrate real callers and delete superseded code and
   dependencies. Run focused checks while iterating and the relevant broader checks on the final
   state. Small verified steps are a tactic, not a ceiling: substantial redesign or replacement is
   in scope when it resolves the problem better and can be verified.
7. **Assess** the final diff against the requirements and show the design benefit: one rule change
   reaches every caller, policy runs without transport setup, resources have explicit owners, a
   library replaced custom machinery, or a real change became easier. Compatibility tests, line
   counts, and file splits alone do not establish improvement. Stop when outcome and gates are met.

## Integrity and reporting

- Never weaken valid assertions or lint, type, or test configuration; delete or skip valid tests;
  change expectations to match output; add blanket suppressions or `cast(Any, ...)` escapes;
  present static reading as runtime evidence; or report unexecuted or stale checks as passing.
  Investigate failing required checks and repair regressions the change introduced.
- When a check is unavailable or blocked by an unrelated failure, report what was implemented, the
  limitation, and what would resolve it; verification stays incomplete, and an unchanged limitation
  is not re-argued. Respect separate merge and deployment gates.
- Report concisely: material changes; caller-visible behavior changes, listed separately;
  consequential decisions as `Problem | Selected approach | Benefit | Cost/risk | Verification`;
  exact checks and results; pre-existing failures; remaining gaps. Order review findings by
  consequence and state the basis. Label self-review as such.

## Compose

HTTP contracts: `api-craft`. CLI contracts: `operator-cli`. Unset stack choices: `stack-profile`.
Defect diagnosis: `root-cause`. An unresolved rollout, compatibility, or recovery design goes to
the design owner (`principal-engineer`). When one is unavailable, apply its concern directly.
