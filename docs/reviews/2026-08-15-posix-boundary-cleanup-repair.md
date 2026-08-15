# POSIX process-boundary cleanup repair — 2026-08-15

**Status:** preparation evidence only. No attempt is appended to the typed record, no independent
evaluation is claimed, and no promotion or monitoring is authorized. The typed record stays
`observed`.

| Field | Value |
|---|---|
| Roadmap item | [EVAL-002](../fleet-roadmap.md) |
| Typed record | [`fi_macos_process_group_cleanup_race`](../../evals/improvements/fi_macos_process_group_cleanup_race/record.json) |
| Intake packet | [2026-08-13 macOS cleanup-race intake](2026-08-13-macos-process-group-cleanup-race-intake.md) |
| Parent revision | `0104b55` |
| Subject files | [`evals/codex_trial.py`](../../evals/codex_trial.py), [`evals/test_codex_trial.py`](../../evals/test_codex_trial.py), [`evals/conformance/codex-terra-evaluator-v1.json`](../../evals/conformance/codex-terra-evaluator-v1.json) |

## Conclusion

`[verified]` The post-timeout `EPERM` is repaired by a narrow invariant rather than a broad
exception catch, and the regression set distinguishes the correct fix from the over-broad one the
intake packet warned against.

`[unverified]` The repair is exercised on Linux only in this environment. The record's fourth
success criterion — focused process-boundary tests passing **repeatedly on macOS** — can only be
discharged by the CI matrix, and remains owed until those jobs run on the exact candidate.

## The defect

`[sourced]` Two macOS jobs on PR #106 failed at exact head `a2a046e1` with
`PermissionError: [Errno 1] Operation not permitted` from the final `os.killpg` in
`_close_process_boundary`, while the byte-identical merge tree passed on main.

`[sourced]` On POSIX both helpers had the same body — `os.killpg(process.pid, SIGKILL)` catching
only `ProcessLookupError`. On the timeout path `_terminate_process_tree` kills the group,
`process.wait()` reaps it, and then the `finally` calls `_close_process_boundary`, which kills the
same group again. Once the leader is reaped macOS may answer `EPERM` rather than `ESRCH` for that
process-group id, so the second kill raised out of a `finally` — turning an already-successful
cleanup into a test error, and masking whatever exception was actually in flight.

## The invariant

The intake packet is explicit that blindly swallowing `PermissionError` would be unsafe: it could
hide a first-order failure to terminate descendants. So tolerance is scoped to the one state where
the call is genuinely a re-run of completed work:

| Site | State | Behaviour |
|---|---|---|
| `_close_process_boundary` | leader already reaped (`poll()` is not `None`) | `EPERM` is a no-op |
| `_close_process_boundary` | process still running | `EPERM` → `InstrumentError`, fail closed |
| `_terminate_process_tree` | any | `EPERM` → `InstrumentError`, fail closed |
| both | group already gone (`ESRCH`) | no-op, unchanged |

`[verified]` The initial termination now raises the same `process-tree-boundary-failed` code the
Windows branch uses, instead of letting a bare `OSError` escape to be reinterpreted upstream as
`process-launch-failed`. A termination failure and a launch failure are different facts.

## Red-first evidence

`[verified]` Each fix reverted in isolation against the candidate tree, the focused class re-run,
the file restored from an unmodified copy:

| Reverted to | `PosixBoundaryClosureTests` |
|---|---|
| No `PermissionError` handling in the final close — **the shipped defect** | 2 errors |
| Swallow `EPERM` unconditionally — **the naive fix the intake packet warns against** | 1 failure |
| Initial termination tolerates `EPERM` | 1 failure |
| None (restored) | green |

The middle row is the load-bearing one. A regression set that only proved "the reported error
stops happening" would be satisfied by the unsafe repair; this one is not.

`[verified]` `test_a_successful_kill_is_still_issued_to_the_process_group` pins that the close
actually signals `SIGKILL` to the group, so the tolerance cannot be satisfied by a boundary that
quietly stopped killing anything.

## Determinism and stability

`[verified]` The new tests drive the state directly with a mocked `os.killpg` and a stubbed
`poll()`; they involve no real processes, no sleeps, and no runner timing. They complete in
milliseconds, where the end-to-end timeout test can only reproduce the fault when the runner
happens to lose the race.

`[verified]` The pre-existing real-process tests are retained unchanged and still assert the
descendant marker is absent, which is what keeps the tolerance from hiding a survivor. Five
consecutive `ProcessBoundaryTests` runs and six consecutive full-file runs were green on Linux.

`[verified]` The class is skipped on Windows, where the Job Object branch is taken and the POSIX
path is never reached — a passing result there would be vacuous.

`[verified]` `evals/codex_trial.py` is a pinned member of the nine-file evaluator bundle, so its
digest and size are refreshed in `codex-terra-evaluator-v1.json`. Gate A caught the stale row
before it could ship. Exactly one row changed; the scenario, routing manifest, frozen scenario
digests, and trial shape are untouched, and no live Terra trial was run.

## An error made and corrected during this work

`[verified]` A blunt global replace of `raised.exception.code` → `.reason_code` also hit an
unrelated pre-existing test asserting `SystemExit.code == 19`, breaking it. Caught by running the
full file rather than only the new class, and reverted precisely. The final diff is **insertions
only** — no pre-existing line was altered — which is the check that would have caught it sooner.

## What I did NOT do

- Did not promote or transition the typed record; it stays `observed` with zero attempts.
- Did not broaden `PermissionError` handling beyond the reaped-leader state, and did not touch
  `ProcessLookupError`, the Windows Job Object branch, or the timeout/wait control flow.
- Did not weaken or remove the real-process descendant assertions.
- Did not reproduce the fault on macOS, and do not claim to have. The mechanism is `[sourced]` from
  the intake packet; the repair is verified against an injected `EPERM`, not against a live macOS
  kernel returning one.

## Honest limits

- `[unverified]` That macOS returns `EPERM` for the precise reason assumed here — a reaped leader's
  group id no longer being signallable — is not confirmed by observation. The repair is correct for
  *any* `EPERM` arriving after the leader is reaped, which is why it is scoped by process state
  rather than by a theory of the kernel.
- `[unverified]` Whether a descendant could outlive a reaped leader *and* have its group return
  `EPERM` is not established. If it can, this repair tolerates that case — the real-process
  descendant assertions are the control that would catch it, and they are unchanged.
- The macOS and Windows CI jobs on the exact candidate are owed before this can close.
