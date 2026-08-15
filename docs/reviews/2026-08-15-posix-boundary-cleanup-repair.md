# POSIX process-boundary cleanup repair — 2026-08-15

**Status:** preparation evidence only. No attempt is appended to the typed record, no independent
evaluation is claimed, and no promotion or monitoring is authorized. The typed record stays
`observed`.

| Field | Value |
|---|---|
| Roadmap item | [EVAL-002](../fleet-roadmap.md) |
| Typed record | [`fi_macos_process_group_cleanup_race`](../../evals/improvements/fi_macos_process_group_cleanup_race/record.json) |
| Intake packet | [2026-08-13 macOS cleanup-race intake](2026-08-13-macos-process-group-cleanup-race-intake.md) |
| Candidate revision | `13e6fd4d3f355b0c3c366d999fc8537c4356c3ac` |
| Base revision | `0104b55` (contains none of the repair — do not evaluate this) |
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
| `_close_process_boundary` | a prior kill succeeded **and** the leader is reaped | `EPERM` is a no-op |
| `_close_process_boundary` | nothing was terminated first (every normal-completion path) | `EPERM` → `InstrumentError`, fail closed |
| `_close_process_boundary` | process still running | `EPERM` → `InstrumentError`, fail closed |
| `_terminate_process_tree` | any | `EPERM` → `InstrumentError`, fail closed |
| both | group already gone (`ESRCH`) | no-op, unchanged |

The first row's *two* conditions are the correction from review round 1 below. An earlier revision
required only the reaped leader, which is not evidence that anything was killed.

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

## Review round 1 — a defect in the repair itself

`[verified]` Independent review on PR #114 found that a reaped leader is **not** evidence the group
was terminated. On every normal-completion path `_terminate_process_tree` is never called: the
leader exits by itself, `poll()` is already non-`None`, and the final close is the FIRST AND ONLY
kill of the group — the one that removes a descendant the leader spawned before exiting, which
`test_normal_bounded_binary_parent_cannot_leave_a_descendant` depends on. The first condition
silently accepted an `EPERM` there and let the descendant escape.

That is the failure this boundary exists to prevent, reintroduced by the repair for a different
one. It is also the exact case this packet listed as least certain — review supplied the concrete
path the author could not.

`[verified]` Tolerance now requires a prior successful kill **and** a reaped leader. `terminated` is
threaded from each `_terminate_process_tree` call site — it raises on `EPERM` and returns on
`ESRCH`, so a normal return is positive evidence — and defaults to `False`, the safe reading for
every path that terminated nothing.

| Reverted to | `PosixBoundaryClosureTests` |
|---|---|
| `poll()` alone, no termination fact — **the reviewed defect** | 1 failure |
| Swallow `EPERM` unconditionally | 2 failures |
| None (restored) | green |

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
