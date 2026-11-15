# Refactoring and migration

## 1. Diagnose and choose

State the design problem before editing (a policy with several owners, decisions tangled with
I/O, representable invalid states, bespoke machinery, the wrong algorithm, forwarding-only layers)
and the improvement that fixes it.

| Approach | Choose when |
|---|---|
| Focused refactoring | The problem is local and the surrounding structure is sound |
| Staged replacement | Consumers cannot move together, behavior is uncertain, or the system must keep shipping mid-change |
| Rewrite | The structure is the problem, required behavior is established or can be, and callers are controlled or the contract is narrow |

Weigh coupling, recoverability, behavioral uncertainty, and expected benefit. Size the process to
the change: most refactors are one coherent change, not a migration program. Clear, tested code
with no demonstrated problem stays.

## 2. Establish contracts

- Find consumers that static references miss: re-exports, entry points, dotted import strings in
  configuration, registries, persisted qualified names, CLI flags and exit codes, log and metric
  names, file and wire formats. Search names as text; a leading underscore proves nothing.
- Classify each observed behavior. **Required** (documented, tested, or relied upon): preserve.
  **Accidental:** free to change. **Defect:** fix when established and in scope. When evidence
  cannot settle the correct behavior, ask; neither preserve nor "fix" on a guess.
- Characterize at behavioral boundaries (public API, CLI, HTTP, files): values and their types,
  exceptions, effect order, cleanup.

## 3. Techniques

| Need | Technique |
|---|---|
| Swap an implementation behind stable callers | Dependency inversion: introduce the seam, move callers, replace; inline the seam if nothing else needs it |
| Old and new must coexist | Branch by abstraction; mark the old public path with `warnings.deprecated` |
| One edit at many sites | A syntax-aware codemod (LibCST, ast-grep, Ruff fixes), tested on matches, near-misses, and migrated code; a second run changes nothing |
| A broad equivalence claim | Differential tests of old against new over generated inputs, plus independent expectations so an old bug cannot pass as correct |
| Persisted data or format change | A versioned migration, old data readable during rollout, tested on realistic old data |

## 4. Equivalence traps

- `all`, `any`, `and`, `or` short-circuit: skipped calls lose their effects and errors.
- Generators defer work and errors and iterate once; `zip` truncates unless `strict=True`.
- Moving to a dict or set changes duplicate handling and ordering, and needs hashable keys.
- Identical code serving unrelated policies is not duplication; share only a common rule.

## 5. Finish

Confirm superseded code and unused dependencies are gone by type checker and text search; static
dead-code tools miss dynamic lookups.
