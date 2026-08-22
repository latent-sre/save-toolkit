# Retire the ROUTE-001 Codex/Terra evaluator

- **Original date:** 2026-08-11
- **Final decision:** 2026-08-22
- **Status:** accepted; evaluator retired
- **Scope:** all Codex/Terra ROUTE-001 execution, container, conformance, and dedicated test files

## Decision

Remove the Codex/Terra evaluator from the active tree. It is no longer a verification surface, a
backlog item, or standing authority for paid model calls. The canonical Claude behavioral runner and
its deterministic graders remain active.

This retirement removes the final Linux preflight and single canary as well as the already-retired
Windows and 48-trial campaign designs. It is not a passing result and grants no baseline, release,
routing, or owner-acceptance authority.

## Why

The remaining canary had answered the useful bounded question. At exact evaluator commit
`cd76ef58e75d5e0fc3d1fa191cbe9bcb851e069e` and immutable image
`sha256:2ddd1652e8ceb8afa0c68146ad0d4399a4068d1e09f4c64c730c55985c39a06b`, target-blind
`gcp-ops` description selection passed 3/3 and the explicitly selected body passed 1/3. The two body
failures isolated one deterministic repository contradiction: the skill requested a Bash fence while
the scenario permitted exactly one JSON fence.

That contradiction belongs in the contract, not in another paid sweep. The canonical skill now says
never to add a fenced block the caller did not permit, and `evals/test_graders.py` fails if that rule
or its fence-free answer shape is removed. No live rerun is needed to prove an offline text contract.

Keeping the instrument would retain provider/version pins, an immutable container, auth handling,
snapshotting, receipts, result reduction, and eight dedicated suites without a named release or
product question. A survivor count, repetition target, or available evaluator is not itself a
finding. Unpublished release contracts and grader state unavailable to the model are not valid
targets for a provider sweep.

## Preserved evidence and recovery

The dated [Linux canary packet](../reviews/2026-08-20-route001-linux-canary.md) preserves the six-call
diagnostic, limitations, exact revisions, image digest, and compact artifact digests. Earlier dated
reviews remain historical evidence with their original labels. Git commit
`0d95ba5de9fe38e4c601fc1eea4ff4bfab4e6fb9` retains the final runnable evaluator bytes.

Recovering those bytes does not reactivate their assumptions or grant execution authority. A future
Codex-specific run requires all of the following:

1. one named uncertainty that offline source, fixtures, and the active runner cannot settle;
2. a current evaluator designed for that uncertainty and independently reviewed at an exact SHA;
3. an explicit owner, budget, and stop condition; and
4. a new accepted decision if the work restores a persistent repository surface.

The old campaign, canary, and call counts are not defaults for that future decision.
