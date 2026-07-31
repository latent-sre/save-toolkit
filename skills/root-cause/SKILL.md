---
name: root-cause
description: >-
  Use when debugging any bug, test failure, or unexpected behavior — before proposing a fix — and
  especially after a fix attempt has already failed, or when guessing has started ("maybe it's X,
  let me try changing it"). Triggers: 'debug this failure', 'why did this test fail', 'the fix did
  not work'. For a production incident with an unknown cause, the `sre` agent owns the investigation;
  this skill is the method it (and sde) load.
argument-hint: "[the bug or unexpected behavior]"
---

> **Evidence default — `[unverified]`.** Unless a paragraph carries a narrower label, each
> stack/product-specific command, query, API or CLI behavior, version, licensing statement, and
> runtime claim in this skill and its bundled files is `[unverified]` for the exact target.
> A narrower `[sourced]` or `[verified]` label takes precedence; handoffs never upgrade it.

Announce at start: "Using root-cause: reproduce → evidence → hypothesis → verify → fix."

Core rule: **find the root cause before attempting any fix.** A fix without a diagnosis is a guess, and guesses compound — each one changes the system you're debugging.

## The loop

1. **Reproduce it.** A bug you can't trigger on demand isn't understood. Capture the exact command and the exact output. If it's intermittent, find what makes it more likely before proceeding.
2. **Read the actual evidence.** The full error (not the summary line), the logs around the failure, and what changed recently — code (`git log -p`), config, dependencies, environment. Most bugs are new; most new bugs come from the last change.
3. **Form ranked hypotheses.** Two or three, most likely first — each paired with the observation that would confirm or kill it. A hypothesis you can't test against evidence is a hunch, not a hypothesis.
4. **Test the cheapest one first.** One instrumented check or experiment per hypothesis — add a log line, run the narrower test, inspect the actual state. Change no behavior yet.
5. **Fix the cause and prove it.** Where the codebase supports it: write the failing test that reproduces the bug, make it pass, then re-run the original reproduction from step 1.

## The three-strikes rule

Three failed fix attempts means the diagnosis is wrong — not that a fourth patch is needed. Stop. Re-read the evidence from scratch, and question the layer: the bug may live in the architecture, the environment, or your mental model of the system, not in the line you keep editing.

## Red flags — stop and restart the loop

- "Let me just try changing X and see"
- "It's probably X" — without an observation that distinguishes X from the alternatives
- Fixing a symptom in a different place each attempt
- Wanting to delete and rewrite a component because the bug is annoying rather than understood

## Worked example (the hypothesis table is the method)
*Symptom: `test_export` passes locally, fails in CI since ~Tue.* Rank by likelihood × cheapness-to-test:

| # | Hypothesis | Likelihood | Test (cheap → dear) | Result |
|---|---|---|---|---|
| 1 | CI uses a different TZ → date assertion off by one | high | print `date` in CI; freeze the clock in the test | **confirmed** — CI is UTC, dev is ET |
| 2 | Dependency bump changed CSV quoting | med | `git diff` the lockfile around Tue | ruled out (no change) |
| 3 | Test order / shared temp file | low | `pytest -p no:randomly` vs shuffled | ruled out |

Causal chain: *unpinned test clock → asserts a localized date → passes in ET, fails in UTC CI.* Minimal
fix: inject/freeze the clock; **regression test** asserts the export under a fixed TZ (fails without the
fix). Note the contributing factor — the env difference — not just the proximate assertion.
