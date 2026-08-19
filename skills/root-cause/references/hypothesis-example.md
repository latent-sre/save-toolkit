# Hypothesis example

Use this shape when a diagnosis has multiple plausible explanations. Do not copy its technologies as
assumptions for another failure.

**Symptom:** `test_export` passes locally and fails in CI after a recent change window.

| Rank | Hypothesis | Confirming observation | Falsifying observation | Cheapest safe check | Result |
|---|---|---|---|---|---|
| 1 | CI timezone changes the asserted date | Same input produces a different local date under CI timezone | Failure persists with a fixed clock and timezone | Record timezone; rerun with fixed clock | Confirmed |
| 2 | Dependency update changed CSV quoting | Lockfile changed in the window and old/new versions differ | No relevant lockfile or behavior difference | Diff the lockfile; compare one fixture | Ruled out |
| 3 | Test order shares a temporary file | Isolated test passes but ordered suite fails with the same file | Failure persists in isolation with a fresh directory | Run isolated and shuffled with traced paths | Ruled out |

```text
Trigger: environment supplies a different timezone
Root cause: test derives an assertion from the ambient clock/timezone
Contributing condition: local and CI environments differ without the test declaring that dependency
Fix: inject or freeze the clock/timezone
Proof: regression test fails before the fix and passes under both environment settings after it
```

The table matters because each check changes belief. A list of plausible causes without confirming and
falsifying observations is brainstorming, not diagnosis.
