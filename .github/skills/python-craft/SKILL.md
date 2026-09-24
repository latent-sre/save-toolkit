---
name: python-craft
description: >-
  Write, refactor, or modernize Python in services, CLIs, scripts, libraries, and tests,
  routine or difficult: simplify structure, reduce duplicated logic, fix established
  defects, and replace custom machinery with suitable maintained libraries. Load before
  editing any Python; also use for explanations and practical starting designs.
  Triggers: 'improve this Python', 'refactor this Python', 'modernize this module',
  'explain this Python'. Not for operating a running service or changing another
  language; backend-craft and operator-cli retain their interface contracts.
argument-hint: "[Python code, file, or task]"
---

# Python craft

Write, fix, and improve Python so it is correct, clear, and cheap to change. Keep clear code when a
change offers no benefit.

## Match the request

| Request | Do | Stop at |
|---|---|---|
| Fix a defect or make a small change | Reproduce it with a failing test or one-line command, change only what the fix needs, rerun it green. Load `root-cause` first when the cause is not established | The fix and its regression check; name other improvements in the return instead of making them |
| Improve, refactor, or modernize | Follow Improve the code below | The agreed scope, with obsolete code removed |
| Write new code or a starting design | Choose a useful approach, explain its main tradeoff, and avoid the classes in [Finding defects](./references/finding-defects.md) | Working code with tests for its failure paths |
| Hunt for bugs or review for defects | Run the detector and read for the classes in [Finding defects](./references/finding-defects.md) | Findings with `file:line`, a reproduction, and a label; source changes only when asked |
| Explain code | Stay read-only; trace behavior at the reader's level, running a snippet to show real output when an interpreter is available | The explanation |

This skill adds no tools or authority beyond the caller's task. Load `backend-craft` too when the
change touches an HTTP service, client, or integration contract, and `operator-cli` when it touches
a command's flags, output, or exit codes; their contract sets the scope, and this skill governs the
Python inside it.

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
  Before choosing a library, tool, or runtime, load `stack-profile`; preserve project conventions and
  component-specific floors, including isolated standard-library-only entrypoints.

## Load the detail that applies

| Task | Read |
|---|---|
| Running code/checks, environment setup, or unexpected check results | [Environment and checks](./references/environment-and-checks.md) |
| Function/data design, typing, errors, or resource ownership | [Writing Python](./references/writing-python.md) |
| Improving existing code, reducing duplication, or restructuring | [Refactoring](./references/refactoring.md) |
| Adopting libraries, replacing custom infrastructure, or changing dependency/runtime APIs | [Libraries and modernization](./references/libraries-and-modernization.md) |
| Automated refactoring, repeated migration, or lint fixes | [Refactoring tools](./references/refactoring-tools.md) |
| Bug hunting, defect review, or code that calls HTTP, subprocesses, clocks, money, or async | [Finding defects](./references/finding-defects.md) |

Load matching references, not the entire bundle.

## Verify and return

For changes, verify affected behavior and failure paths through existing callers, plus the claimed
improvement. Before restructuring, show that the tests reach the code being moved (Refactoring
covers how). Fewer lines or a successful tool run proves neither. Use project checks; profile and
benchmark performance claims separately. Remove code and dependencies made obsolete by the change.

Return the benefit or fix, intentional behavior changes, checks/results, and gaps with
`[verified]`, `[sourced]`, or `[unverified]`. After a fix or small change, add a **Noticed, not
changed** line naming each defect, duplication, or cleanup you saw in the files you read but left
alone, or `none`. Explain the useful decision, not every mechanical edit.
