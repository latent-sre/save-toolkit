# Active backlog exact-subject review -- 2026-08-19

**Status:** independent local correctness/security review and preparation evidence for `ROUTE-001`,
`MUTATION-001`, `EVAL-002`, and `SCRIPTS-001`. This packet does not append a typed-record attempt or
review, resolve GitHub threads, provision a protected evaluator host, authorize credentials, run a
Terra canary, or run the 48-trial routing campaign.

## Conclusion

| Item | Exact subject reviewed | Verdict | Remaining gate |
|---|---|---|---|
| `ROUTE-001` | PR #113 final head `9a5dbe648995013134fcb63ede3d917275982ad5` | **PASS** for the grader repair; no P0/P1 correctness or security finding | Bind the verdict to the typed record, then satisfy the protected-runtime and clean-host prerequisites before a one-trial canary |
| `MUTATION-001` | PR #116 final head `ccceb33bc6ff4de3608fc0c5c2188b34b050bb4b` | **CHANGES REQUESTED** for an uncovered documented input: the guard is correct, but `--limit 0` was not mutation-pinned | Independently review test-only commit `ec35aad33d97970a0a1b3c76598344f3bf10f857`, produce the fresh envelope, and retain the retrospective chronology limit |
| `EVAL-002` | PR #114 final head `106ee282903076dc54020df295ac37a0e66bc9d8` | **PASS**; the two-fact POSIX cleanup invariant held in static review and exact Windows/Linux execution | Bind a fresh envelope and exact-revision verdict to the typed record; do not broaden the `PermissionError` catch |
| `SCRIPTS-001` | PR #119 final head `9fef1486ffd98bfcf6362d5c88b62e0a018b67e6`, over PR #118 merge `4479833fcb2d64059c6aa8047dbc8370b95584f3` | **PASS**; the candidate-parser execution path is closed and no P0/P1 remains in the whole diff | Reconcile and resolve the still-open PR #118/#119 review threads, then close the roadmap item |

The three pass verdicts are bound to immutable Git commits and were produced from a separate clean
clone. The mutation follow-up is not independently approved by this packet: the same operator that
found the missing assertion authored `ec35aad`, so that commit deliberately remains a review
candidate.

## Workspace and subject control

`[verified]` `origin/main` was refreshed to
`78a41c41809d533bded136ad1cc944811dbfe6a7` (merge of PR #120) before any work started.

`[verified]` The original checkout was on `fix/settings-deny-rule-namespaces` and already contained
large deletions under generated adapter roots. Those changes were treated as user-owned and left
untouched. No reset, checkout-based restoration, stash, clean, or broad staging was used.

`[verified]` Exact-subject execution and review took place in a separate normal clone on branch
`work/active-backlog-evidence`. Historical subjects were checked out detached by full SHA; the
working branch was restored before the mutation regression was authored.

`[verified]` The `evals/graders.py` implementation for the grader repair and both POSIX-cleanup
target files are byte-identical between their final PR heads and refreshed main. PR #120 added a
routing fixture, changing `evals/test_graders.py` from blob
`ec3a61e0cf5174c50b14eed840479bee27f4046d` at PR #113 final head to
`1418971191b02791eeae2540c087d8e4f53ed1e7` in refreshed main. The PR #119 evaluator hardening is
present in refreshed main through its merge.

## ROUTE-001 -- grader repair

### What was reviewed

The review covered the final PR #113 grader implementation, its focused tests, and the call order
that rejects an outside-packet command before accepting the packet's JSON commands. The normalizer:

- removes POSIX line continuations with the empty string, preserving shell word joining;
- strips single and double quote markers;
- removes backslash escapes instead of replacing them with spaces;
- normalizes whitespace and case; and
- searches the normalized outside-packet text before JSON packet acceptance.

`[verified]` This closes the reviewed `gcl\oud`, `serv\ices`, `update\-traffic`, and continuation-
inside-word bypasses. The existing intentional over-rejection of `services\ update-traffic` remains
documented rather than being mistaken for shell-parser equivalence.

### Fresh execution

At `9a5dbe648995013134fcb63ede3d917275982ad5`:

```text
python evals/test_graders.py
test_graders: 342/342 checks passed.
exit 0
```

`[verified]` Static correctness/security review found no remaining P0/P1 in the repair.

`[unverified]` The normalizer is not a full shell parser. Command substitution, variable expansion,
`eval`, encoded command construction, and here-document assembly remain outside its established
contract. No live model call was made, so this result is instrument evidence only.

### GitHub reconciliation

PR #113 still showed two unresolved but outdated review threads. The final head contains the
author's fixes for both, but this work did not mutate GitHub state. The pass verdict above is the
missing exact-head technical judgement; a typed-record binding and thread disposition remain
separate actions.

## MUTATION-001 -- exact subject and new regression

### Exact historical subject

At `ccceb33bc6ff4de3608fc0c5c2188b34b050bb4b`:

```text
python scripts/test_mutation_guard.py
Ran 49 tests in 15.855s
OK (skipped=2)
exit 0
```

The three defects named by `MUTATION-001` remain repaired: sampled results do not claim total
non-exercise, usage/refusal/inconclusive/survivor exits remain distinct, and the sampling text does
not claim coverage of a named mutant.

### The guard turned on itself

An unbounded exact-subject sweep was then run deliberately:

```text
python scripts/mutation_guard.py --module scripts/mutation_guard.py --limit 0
48 surviving mutants
exit 1 (EXIT_SURVIVORS)
```

The survivor count is not itself a claim that 48 production defects exist. Many mutants are
equivalent, near-equivalent, or outside the load-bearing behavior of this item. One survivor was
directly actionable:

```text
scripts/mutation_guard.py:492
if value < 0:        ->        if value <= 0:
```

The documented contract says zero means an unbounded sweep. The exact mutant rejected zero as a
usage error, yet the then-current suite stayed green. Current behavior was correct; its assertion
was missing. Because the tool exists to expose precisely this false-green shape, the exact-subject
review is `CHANGES REQUESTED` rather than silently accepting the gap.

### Test-only repair

Commit `ec35aad33d97970a0a1b3c76598344f3bf10f857` adds one public-behavior regression:

```text
test_zero_limit_runs_the_documented_unbounded_sweep
```

`[verified]` Red check: with only the exact `< 0` to `<= 0` mutant applied, the new test failed
because the guard returned `EXIT_USAGE` (4) for `--limit 0` instead of the clean result (0).

`[verified]` Green check: after restoring the implementation byte-for-byte, the new test passed;
the whole focused file then reported 50 tests run, 2 skipped, and exit 0.

`[verified]` The first attempted one-test red invocation failed to import `mutation_guard` because
it was launched from the repository root. That run is excluded from defect evidence. The test was
rerun from `scripts/`, where it failed on the intended assertion, and only that corrected run is
used above.

`[unverified]` `ec35aad` has not received independent review. This packet does not backfill a normal
pre-merge lifecycle: PR #116 predates the linked record and evaluation, and the linked record must
retain that retrospective chronology.

## EVAL-002 -- POSIX process-boundary cleanup

### Invariant reviewed

At `106ee282903076dc54020df295ac37a0e66bc9d8`, `terminated` starts false and becomes true only after
`_terminate_process_tree` returns successfully. Final POSIX closure tolerates `PermissionError` only
when both facts hold:

1. a prior group termination succeeded; and
2. the leader has been reaped (`poll()` is non-`None`).

The initial termination path never tolerates `PermissionError`. Missing either fact remains a
fail-closed `process-tree-boundary-failed` instrument error, preserving the descendant guarantee.

### Fresh exact-subject execution

Windows host:

```text
python evals/test_codex_trial.py
Ran 48 tests in 5.981s
OK (skipped=6)
exit 0
```

Pinned Linux container:

```text
docker run --rm --network none --read-only --cap-drop ALL \
  --security-opt no-new-privileges --user 65532:65532 \
  --tmpfs /tmp:rw,noexec,nosuid,nodev,size=64m \
  -v <exact-checkout>:/repo:ro -w /repo \
  python@sha256:13c9584604a99ca134c4f41800f74ffc64ee6ac8cf555cf1e704a6087fc84f12 \
  python evals/test_codex_trial.py
Ran 48 tests in 9.950s
OK (skipped=2)
exit 0
```

`[verified]` The Linux execution covers the real POSIX descendant tests as well as the deterministic
injected `PermissionError` seam. Static correctness/security review found no remaining P0/P1.

`[unverified]` This work did not reproduce a live macOS kernel returning the original intermittent
`EPERM`. Existing exact-byte GitHub matrices supply the repeated macOS execution already cited by
the roadmap; this packet adds deterministic Windows/Linux evidence and the missing exact-head
judgement, not a new macOS observation.

PR #114 still showed two unresolved but outdated P1 threads whose fixes are present in the final
head. They were not resolved here.

## SCRIPTS-001 -- final whole-diff review

### Security boundary

PR #118's P1 was valid: loading the measured plugin's `scripts/fleet_frontmatter.py` in the
evaluator parent executed candidate top-level code with the evaluator's authority.

At PR #119 final head `9fef1486ffd98bfcf6362d5c88b62e0a018b67e6`, the reviewed boundary is:

- the trusted parser is taken from the frozen evaluator bundle;
- the measured parser is compared as bytes and is never imported in the evaluator parent;
- parser drift fails closed before a measured child runs;
- the trusted parser is preloaded before cross-trial candidate mutation is possible;
- the evaluator-support digest changes when the trusted parser changes;
- the direct-agent tool tuple is frozen before the candidate child starts; and
- teardown assertions verify the trusted parser does not leak in the parent after the test.

`[verified]` These controls remove the source-to-sink path reported on PR #118. Review of the full
`4479833..9fef148` diff found no remaining P0/P1 correctness or security issue.

### Fresh exact-head structural execution

```text
docker run --rm --network none --read-only --cap-drop ALL \
  --security-opt no-new-privileges --user 65532:65532 \
  --tmpfs /tmp:rw,noexec,nosuid,nodev,size=128m \
  -e PYTHONDONTWRITEBYTECODE=1 -v <exact-checkout>:/repo:ro -w /repo \
  save-toolkit-gate@sha256:2c22bac63f6ce8e12bc240e04918493f2e03c83c364972c03e7418d2190bc9cb \
  python scripts/gate_a.py
Gate A: PASS -- 40/40 structural steps green.
exit 0
```

The run included 73/73 `evals/test_run_evals.py` tests and 342/342 grader checks. Gate A proves the
tree is well-formed, not correct; the whole-diff judgement above is the separate review result.

PR #118 still has the original non-outdated P1 thread open. PR #119 still showed five unresolved
threads covering digest binding, teardown, roadmap reconciliation, stale next-action text, and the
retrospective improvement-record status. The final head contains fixes for all five, but this work
did not resolve or reply to any thread.

## Excluded and corrected environment failures

`[verified]` Initial unprivileged Windows runs of `test_mutation_guard.py` and
`test_codex_trial.py` encountered `PermissionError` while creating directories under the managed
temporary root. They were sandbox/environment failures, not product failures. Both commands were
rerun with normal temporary-directory access; only the successful reruns are used as subject
evidence.

`[verified]` The first PR #119 Gate A output exceeded the orchestration output window. The same
exact command, commit, image digest, and isolation flags were rerun with only the final output
retained; that run completed with exit 0 and the 40/40 result recorded above.

## Final branch validation

`[verified]` After adding `ec35aad` and this documentation, the complete branch worktree passed all
40 Gate A structural steps in the same pinned, network-disabled, read-only container. The run
included the 50-test mutation-guard file (2 platform skips), 48 POSIX trial tests (2 platform skips),
345/345 current grader checks, and 73 evaluator-runner tests. This proves the branch is well-formed;
it does not independently approve the author-written mutation test.

## Subsequent work

This dated packet is round-closure evidence, not an actionable queue. The only live backlog and the
governing next actions are in [`docs/fleet-roadmap.md`](../fleet-roadmap.md).

## What I did NOT do

- Did not modify or clean the user's original dirty checkout.
- Did not change production, GitHub settings, environments, rulesets, credentials, or live systems.
- Did not call a model, run a Terra canary, implement the 48-trial executor, or claim a routing
  baseline.
- Did not append, promote, reject, or otherwise transition an improvement record.
- Did not reply to or resolve a GitHub review thread.
- Did not claim the author-written `ec35aad` test commit has independent approval.
