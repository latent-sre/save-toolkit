---
name: python-craft
description: >-
  Improve difficult Python code in services, CLIs, scripts, libraries, and tests:
  simplify structure, reduce duplicated logic, fix established defects, and replace
  custom machinery with suitable maintained libraries. Use for refactoring,
  modernization, writing new code, explanations, and practical starting designs.
  Triggers: 'improve this Python', 'refactor this Python', 'modernize this module',
  'explain this Python'. Not for operating a running service or changing another
  language; backend-craft and operator-cli retain their interface contracts.
argument-hint: "[Python code, file, or task]"
---

> **Copilot adapter:** Fleet component names are bare in this generated copy.
> Resolve them from the installed plugin using the host's agent or skill picker.

# Python craft

Improve difficult or repetitive Python through better design and implementation. Keep clear code
when a change offers no benefit.

## Match the request

For improvement requests, carry justified changes through callers and tests, not just recommendations.
For new code or a starting design, choose a useful approach and explain its main tradeoff. For review
or explanation alone, stay read-only: trace behavior and adapt detail to the reader without imposing
a build workflow. This skill adds no tools or authority beyond the caller's task.

## Improve the code

- Establish required behavior from the request, callers, specifications, and tests. Existing behavior
  is evidence, not proof of correctness. Reproduce defects and confirm expected fixes; distinguish
  intentional behavior changes from restructuring rather than guessing intent.
- Find the highest-value problem: duplicated policy, tangled responsibilities, awkward data flow,
  fragile effects, or unnecessary machinery. Choose a coherent solution, not a line-count target.
- Work in medium-sized, coherent stages: complete a meaningful improvement across related files,
  then verify it. Stages are checkpoints, not a limit on how much code may ultimately change.
- Reshape or rewrite any or all code in scope when justified, including controlled callers. Remove
  obsolete layers and use suitable libraries within project constraints. Preserve supported contracts;
  seek direction for unresolved requirements or material compatibility, runtime, framework, or
  live-system changes not already authorized.
- Compare direct code, standard-library features, existing dependencies, and maintained packages.
  Before implementation or tooling choices, load `stack-profile`; preserve project conventions and
  component-specific floors, including isolated standard-library-only entrypoints.

## Load the detail that applies

| Task | Read |
|---|---|
| Running code/checks, environment setup, or unexpected check results | [Environment and checks](./references/environment-and-checks.md) |
| Function/data design, typing, errors, or resource ownership | [Writing Python](./references/writing-python.md) |
| Improving existing code, reducing duplication, or restructuring | [Refactoring](./references/refactoring.md) |
| Adopting libraries, replacing custom infrastructure, or changing dependency/runtime APIs | [Libraries and modernization](./references/libraries-and-modernization.md) |
| Automated refactoring, repeated migration, or lint fixes | [Refactoring tools](./references/refactoring-tools.md) |

Load matching references, not the entire bundle. Compose with `backend-craft` for service/integration
contracts, `operator-cli` for command behavior, and `root-cause` for defect diagnosis.

## Verify and return

For changes, verify affected behavior and failure paths through existing callers, plus the claimed
improvement. Fewer lines or a successful tool run proves neither. Use project checks; profile and
benchmark performance claims separately. Remove code and dependencies made obsolete by the change.

Return the benefit, intentional behavior changes, checks/results, and gaps with
`[verified]`, `[sourced]`, or `[unverified]`. Explain the useful decision, not every mechanical edit.
