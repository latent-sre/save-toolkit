# Incident-navigation archive

**Status:** accepted 2026-08-22; disposes `NAV-001`.

## Decision

Reject `incident-navigation` as a fleet feature and remove it from the live roadmap. The fleet has
moved on and is simplifying its skills; restarting this candidate would restore machinery that no
longer fits that direction.

Keep the existing evidence in place:

- remote branch `feat/incident-navigation` at
  `9a545123e440dec474d13d13f9e1cf460d692fe9`;
- the hash-bound
  [`prototype preservation packet`](../reviews/2026-08-12-incident-navigation-preservation/README.md).

This decision does not authorize deleting the branch or packet. Do not rebase, merge, publish,
rerun, or repair the candidate.

## Why

The candidate adds 26 unique commits and roughly 5,600 lines across 46 files for a narrow responder-
orientation problem. Its deterministic checks passed, but its exact-candidate Sonnet campaign passed
only 1 of 10 scenarios and 3 of 20 complete trials; independent review also found a P1 fail-open in
the no-execution grader. Current main ships no `incident-navigation` component, so rejection removes
no accepted behavior.

At disposition time the remote branch had no pull request and was 108 commits behind current main.
The current checkout contained neither of the parked worktrees nor the ten raw run directories. The
original preservation packet still verified 11 of 11 patch digests, so the historical idea remains
recoverable without keeping it in the active backlog.

## Reopen trigger

Reopen only when an actual incident demonstrates that the existing `sre` lane cannot identify the
first evidence source for a responder. Start with a small clarification in `sre`; do not restore the
archived skill or its grader suite by default.
