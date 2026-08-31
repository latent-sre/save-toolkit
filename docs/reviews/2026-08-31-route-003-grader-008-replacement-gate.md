# ROUTE-003 and GRADER-008 replacement approval gate

> **Status:** `[verified]` Owner approval is recorded in both one-time replacement profiles.
> ROUTE-003 executed once and ended terminally `INCONCLUSIVE` after the subscriber OAuth session
> expired and could not be refreshed. GRADER-008 remains approved and unstarted pending restored
> authentication.

## Why a replacement is now eligible for owner decision

The original ROUTE-003 and GRADER-008 packets are consumed and remain terminal INCONCLUSIVE
evidence. They are never overwritten or relabelled. Each failed before resolving a model after the
same Claude Code 2.1.251 path exhausted provider retries with `server_error`:

- [`ROUTE-003 batch 20260831T045127Z-b6efb49b`](2026-08-31-eval-20260831T045127Z-b6efb49b.md)
- [`GRADER-008 batch 20260831T051130Z-d1887391`](2026-08-31-eval-20260831T051130Z-d1887391.md)

The same host, CLI version, subscriber authentication mode, and requested Sonnet tier subsequently
produced the complete, resolved-model, conclusive nine-trial
[`GRADER-005 batch 20260831T052440Z-c13a16f0`](2026-08-31-eval-20260831T052440Z-c13a16f0.md).
That is the named material provider/runtime recovery signal. It does not itself authorize a retry;
it only satisfies the roadmap prerequisite for a new owner decision.

## Fixed replacement cells

| Item | Exact candidate | Profile | Scenarios | Trials | Timeout | Ceiling |
|---|---|---|---|---:|---:|---:|
| ROUTE-003 | `38dbdf70722c2167ce2c404297ccb4ccc3f5da8f` | `route-003-discovery-reliability-replacement-1` | `discovery-agent-authoring-workflow-graph`; `discovery-service-readiness-audit` | three each; six calls maximum | 600 s/trial; 7,200 s total | USD 4 |
| GRADER-008 | `7d9aa18c4efb223060b27685d0dd0be4e8590059` | `grader-008-sre-progressive-object-replacement-1` | `agent-direct-sre-readonly-triage` | three calls maximum | 600 s/trial; 2,400 s total | USD 2 |

Both use native Claude `sonnet`, a clean detached candidate, `--require-clean-plugin`, unchanged
scenario thresholds, and the current approved evaluator bytes. The replacement profiles differ
from the consumed profiles only in profile identity and approval state; they do not tune a prompt,
description, scenario, grader, split, threshold, model, candidate, timeout, or budget.

Approval was recorded at `2026-08-31T11:44:14Z` in commit
`f820b287c663a8b611f0e2d0a1d594f97609ca80`, under the owner-authorized
ceiling of 50 runs per backlog item. The narrower profile ceilings and one-execution retention rules
below continue to govern these cells.

## Execution update

ROUTE-003 batch
[`20260831T114601Z-72bffc6d`](2026-08-31-eval-20260831T114601Z-72bffc6d.md) executed its six
planned calls once on exact candidate `38dbdf70722c2167ce2c404297ccb4ccc3f5da8f`. All six ended
`INCONCLUSIVE` before model resolution with `Failed to authenticate: OAuth session expired and
could not be refreshed`; integrity remained `PASS`. The batch is retained and will not be retried.
The GRADER-008 cell was deliberately not started against that known-unusable session.

Prepared profiles:

- [`ROUTE-003 replacement`](../../evals/profiles/route-003-discovery-reliability-replacement-1-sonnet.json)
- [`GRADER-008 replacement`](../../evals/profiles/grader-008-sre-progressive-object-replacement-1-sonnet.json)

## Stop and retention rules

1. Do not start either cell while its profile approval is null or any fixed field differs.
2. Each cell may run once. Retain PASS, FAIL, timeout, authentication failure, and INCONCLUSIVE.
3. Stop the affected cell on candidate/plugin drift, authentication failure, total-time expiry,
   its cost ceiling, unavailable expected cost, mixed resolved models, or runner-integrity failure.
4. A red or inconclusive replacement authorizes no tuning or second replacement. Return the exact
   evidence to the owner.
5. The two cells are separately approved and separately terminal; one cannot offset the other.

## Commands after explicit approval

From the matching clean detached candidate worktree, pass the approved profile by absolute path:

```powershell
python evals/run_evals.py --run --profile <ABSOLUTE_ROUTE_REPLACEMENT_PROFILE> --results-dir .eval-runs/route-003-replacement-1 --require-clean-plugin
python evals/run_evals.py --run --profile <ABSOLUTE_GRADER_REPLACEMENT_PROFILE> --results-dir .eval-runs/grader-008-replacement-1 --require-clean-plugin
```

The runner captures the sealed summary and normalized envelope into bounded durable evidence. Do
not manually copy raw traces into the repository.

## Approval contract (satisfied)

A sufficient one-message authorization is:

> I approve ROUTE-003 replacement profile `route-003-discovery-reliability-replacement-1` for exact
> candidate `38dbdf70722c2167ce2c404297ccb4ccc3f5da8f`, Sonnet, the two named scenarios at three trials
> each, 600 seconds per trial, 7,200 seconds total, and USD 4 maximum. Budget ID:
> `route-003-discovery-reliability-replacement-1-2026-08-31`. I also approve GRADER-008 replacement
> profile `grader-008-sre-progressive-object-replacement-1` for exact candidate
> `7d9aa18c4efb223060b27685d0dd0be4e8590059`, Sonnet, three trials of
> `agent-direct-sre-readonly-triage`, 600 seconds per trial, 2,400 seconds total, and USD 2 maximum.
> Budget ID: `grader-008-sre-progressive-object-replacement-1-2026-08-31`. Each profile may execute
> once with no tuning or retry; retain every outcome.
