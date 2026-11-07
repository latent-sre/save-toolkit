---
name: python-craft
description: >-
  Write, refactor, modernize, and verify Python code with autonomous
  engineering judgment across scripts, CLIs, libraries, packages, and
  services. Use when designing Python modules or packages, selecting or
  replacing dependencies, restructuring tangled code, modernizing syntax or
  typing, fixing defects, or establishing proportional tests and checks.
  Triggers: "write or refactor Python code", "design a Python module or CLI",
  "modernize Python or replace custom code", "review or test Python changes".
---

# Python Craft

Deliver complete, verified Python changes through focused engineering judgment:

1. **Build new code well from the start**: choose sound libraries, target-version features, data models, module boundaries, interfaces, tests, and checks before weak patterns spread.
2. **Improve existing code deliberately**: diagnose root design flaws, compare stronger alternatives, and implement justified modernization and structural improvement rather than cosmetic diffs.
3. **Improve the refactoring process**: sequence behavior-preserving moves, use suitable tools, establish behavioral evidence, and verify compatibility and concrete design gain.

Preserve required behavior and genuine constraints—not historical implementation choices.

## Engineering Judgment, Autonomy, and Scope

- **Assess opportunities** across libraries, Python features, data models, interfaces, algorithms, module ownership, resource lifetimes, errors, testing, and typing.
- **Compare against the strongest credible alternative** on correctness, clarity, maintainability, compatibility, security, testability, operational fit, migration effort, and recurring maintenance or dependency cost. Neither status quo code nor novelty gets automatic preference.
- **Reject unsupported conservatism**: "avoid dependencies", "keep the diff small", "follow the existing pattern", "the code already works", and "that might be overengineering" are insufficient alone; require a concrete drawback, constraint, or disproportionate cost.
- **Decide autonomously within scope**: select libraries, internal interfaces, module boundaries, algorithms, and tools without redundant prompts. Recommend the best-supported option rather than presenting unequal choices as peers.
- **Escalate only genuine blockers** affecting required behavior, external contracts, persistent data, live systems, or scope; continue independent work meanwhile.
- **Respect boundaries**: preserve unrelated changes; surface constraints blocking better solutions rather than overriding them silently; keep review/explanation requests read-only; report out-of-scope improvements without applying them.
- **Record consequential decisions**: `Problem | Selected approach | Benefit | Cost/risk | Verification`
- **Use small verified steps as a tactic**, not a limit on ambition. Redesign or replace internal structure when it solves the in-scope problem cleanly.

## Proportional Execution Workflow

1. **Inspect**: check instructions, working-tree changes, `requires-python`, consumers, dependencies, tests, and verification commands.
2. **Classify**: distinguish new behavior, behavior-preserving refactoring, modernization, defect repair, and read-only review; separate behavior changes from structural moves.
3. **Define success**: state required behavior, root problem, intended improvement, affected boundaries, and acceptance evidence.
4. **Consult**: load only the reference files matching the task and inspection findings.
5. **Establish evidence**: reuse valid checks or capture a baseline to separate existing failures from regressions. Characterize untested behavior before restructuring; add regression or acceptance tests failing before the fix where practical; skip ceremonial tests for trivial edits or implementation mirrors.
6. **Implement and verify**: deliver a complete working path; iterate with focused checks and run broader gates on the final state.
7. **Assess**: confirm the root problem improved without shifting complexity or turning a trivial edit into an architecture project.

## Reference Routing

| Reference | Load when |
|---|---|
| [`references/design-and-dependencies.md`](references/design-and-dependencies.md) | Designing scripts, CLIs, packages, or services; selecting target-version features; evaluating, adding, replacing, or upgrading libraries; checking anti-patterns. |
| [`references/refactoring.md`](references/refactoring.md) | Diagnosing structural smells; splitting, merging, or removing modules and layers; preserving exports, contracts, and patch seams; choosing refactoring tools (`rope`, `libcst`, `ruff`). |
| [`references/verification.md`](references/verification.md) | Binding the project interpreter (`uv`, `.venv`); designing unit, characterization, differential, property-based (`Hypothesis`), import, or performance checks; reporting verification. |
