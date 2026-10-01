---
name: python-craft
description: >-
  Write, refactor, or modernize Python in services, CLIs, scripts, libraries, and tests,
  routine or difficult: simplify structure, reduce duplicated logic, fix established
  defects, and replace custom machinery with suitable maintained libraries. Load before
  editing any Python; also use for explanations and practical starting designs.
  Triggers: 'improve this Python', 'refactor this Python', 'modernize this module',
  'explain this Python'. Not for operating a running service or changing another
  language.
argument-hint: "[Python code, file, or task]"
---

# Python craft

Make Python easier to understand, use, and change. Keep clear code when a change offers no benefit.
The task and project constraints set scope; this skill adds no tools or authority. Explanation,
design, and review requests stop at those outputs unless implementation is requested. For a defect,
establish the cause and expected behavior, reproduce it, and verify the repair. Keep small changes
scoped; report material adjacent findings separately.

## Build or improve

1. For new code, establish expected behavior and a realistic consumer. For existing code, trace the
   operation and locate coupled state, copied policy, awkward calls, tangled effects, or repeated work.
2. Choose the design or transformation that fits: representations, algorithms, control flow,
   interfaces, extraction or inlining. Compare direct code, the standard library, existing
   dependencies, and maintained packages where relevant.
3. Deliver a complete path through its entrypoint, then cover remaining cases and affected callers.
   Stage work by risk; a justified rewrite may replace all in-scope implementation.
   Preserve supported contracts; separate intentional behavior changes from
   restructuring and resolve uncertain requirements rather than guessing.
4. Check required behavior through intended entrypoints. For refactoring, show the benefit: one policy
   owner, fewer facts callers must coordinate, removed machinery, or an easier real change. Remove obsolete
   code/dependencies; passing tests or reducing line count alone does not establish improvement.

## Load relevant detail

| Task | Read |
|---|---|
| Starting a new script, module, library, or service | [New code](./references/new-code.md) |
| Interpreter/dependencies uncertain or changing | [Environment and checks](./references/environment-and-checks.md) |
| Calls, functions, modules, data, or resource ownership | [Writing Python](./references/writing-python.md) |
| Structural improvement or Pythonic replacements | [Refactoring](./references/refactoring.md) |
| Need a worked comparison for flattening nested control flow | [Guard-clause example](./references/guard-clause-example.md) |
| Library adoption or dependency/runtime migration | [Libraries and modernization](./references/libraries-and-modernization.md) |
| Automated transformations or lint fixes | [Refactoring tools](./references/refactoring-tools.md) |
| Bug hunting, review, or a suspected failure | [Finding defects](./references/finding-defects.md) |

Load matching references only. Use project checks in the intended environment and supported Python
versions. Report the change's benefit, intentional behavior differences, verification, and remaining
uncertainty; measure performance claims separately.
