# macOS process-group cleanup race intake — 2026-08-13

**Status:** `observed`; no repair attempt, review, promotion, or monitoring is claimed.

## Conclusion

`[verified]` The PR #106 macOS validation job and its rerun failed at the same process-boundary test
on exact head `a2a046e1b62902952abc2a9c94192005b6527d93`. Both raised
`PermissionError: [Errno 1] Operation not permitted` from the final POSIX `os.killpg` call in
`_close_process_boundary`. The merge commit `ec2537b9041de190a73573d1446c160bdf340d30`
has the same Git tree (`db4aea646d06dd8b8cd45874b599352daa18f8d8`) and passed the macOS job on
main. This is evidence of a nondeterministic process-cleanup failure, not evidence that the PR's PCF
grader change was incorrect.

`[unverified]` The precise macOS kernel timing or process-group state that returns `EPERM` has not
been reproduced under a deterministic seam. The code shape below is a candidate mechanism, not a
confirmed root cause.

## Frozen observations

| Observation | Exact subject | Result |
|---|---|---|
| [PR job, attempt 1](https://github.com/latent-sre/save-toolkit/actions/runs/31698684810/job/94442273438) | `a2a046e1b62902952abc2a9c94192005b6527d93`; 2026-08-13 12:08:53–12:09:23 UTC | `[verified]` `test_timeout_terminates_the_created_process_tree` errored at `evals/codex_trial.py:1728` with `EPERM` |
| [PR job, attempt 2](https://github.com/latent-sre/save-toolkit/actions/runs/31698684810/job/94445597983) | same SHA; 2026-08-13 12:22:18–12:22:48 UTC | `[verified]` same test, call site, and exception |
| [main job](https://github.com/latent-sre/save-toolkit/actions/runs/31699292341/job/94444248855) | merge commit `ec2537b9041de190a73573d1446c160bdf340d30`; 2026-08-13 12:16:58–12:17:29 UTC | `[verified]` passed on the byte-identical tree |

The failed log was re-read with:

```text
gh run view 31698684810 --repo latent-sre/save-toolkit --job 94445597983 --log-failed
```

Tree identity was rechecked with `git show -s --format=%T` on the PR head and merge commit. No
candidate or historical branch was treated as current code.

## Candidate mechanism and risk

`[sourced]` On the observed code, `launch_process` calls `_terminate_process_tree` when the timeout
expires, waits for the process, and then unconditionally calls `_close_process_boundary` from its
`finally` block. On POSIX, both helpers send `SIGKILL` to `process.pid` as a process-group ID and
catch only `ProcessLookupError`.

`[unverified]` The second `killpg` after the wait may be racing a changed or inaccessible
process-group state. Blindly swallowing every `PermissionError` would be unsafe: it could hide a
first-order failure to terminate descendants and weaken the test's load-bearing guarantee. The
repair therefore needs a deterministic regression and an explicit idempotent-cleanup invariant,
not a broad exception catch justified only by a flaky runner.

## Disposition and bounded next action

The matching typed record is
[`fi_macos_process_group_cleanup_race`](../../evals/improvements/fi_macos_process_group_cleanup_race/record.json).
It remains `observed` because the lifecycle's semantic promotion validators are parked and no
candidate has been prepared.

The next owner should:

1. Add a deterministic seam that reproduces post-timeout cleanup returning `EPERM` after the
   termination-and-wait path.
2. Define the narrow state in which final cleanup is idempotent without suppressing a failed initial
   termination.
3. Keep a mutation-sensitive assertion that the child and descendant are gone after timeout.
4. Run the focused process-boundary tests repeatedly on macOS, the full Gate A matrix, and an
   independent exact-revision correctness/security review.

No code fix was attempted during PR #106 closeout. This packet records the repeated fingerprint so
it is not lost or incorrectly attributed to the grader patch.
