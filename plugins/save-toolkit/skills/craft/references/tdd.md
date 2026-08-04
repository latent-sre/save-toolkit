Read this when writing tests-first or after any bug fix (the regression test is non-negotiable).

## Red → green → refactor
1. **Red.** Write a test that states the desired behavior and **run it — confirm it fails** (and fails
   for the right reason, not a typo/import error).
2. **Green.** Write the minimum code to make it pass. Run the suite.
3. **Refactor.** Clean up with the test as your safety net; keep it green. See the [safe refactoring process](./safe-refactor.md).

## Regression-first for bug fixes (non-negotiable)
Before fixing a bug, write the test that **reproduces it** and **fails on the current (broken) code**.
Then fix and watch it go green. This proves the bug is real and guards against its return.

## What to test
- **Behavior and contracts**, not implementation details — so tests survive refactors.
- Happy path, **edge cases** (empty/null/zero/negative, boundaries, large/unicode, concurrency), and
  **error/failure paths**.
- Inject or freeze nondeterminism (clock, randomness, network) — no flakiness, no order-dependence.
- Prefer many fast unit tests; integration where components meet; a few e2e for critical journeys.

## Frameworks (this team)
Per-language frameworks and setup live in **`craft`** (read the language file) — `pytest` (Python),
`Pester` (PowerShell), `bats` (Bash), Vitest (TS/React), `testing` (Go). This skill owns the *method*
(red-green, what to test); `craft` owns the *tooling*.

## Done
- New behavior is covered; the bug-fix test fails without the fix.
- Suite is green and fast; you state coverage delta and any gaps you left on purpose (and why).
