# ROUTE-003 native discovery reliability approval gate

> **Status:** `[verified terminal evidence]` The fixed execution packet was approved, executed once,
> and consumed by INCONCLUSIVE provider results. It authorizes no retry. Bounded evidence:
> [`20260831T045127Z-b6efb49b`](2026-08-31-eval-20260831T045127Z-b6efb49b.md).

## Exact candidate and purpose

- Plugin candidate: `38dbdf70722c2167ce2c404297ccb4ccc3f5da8f`.
- Candidate posture: clean committed plugin inputs; the later packet-only commit does not alter the
  measured agent, skill, hook, or generated-adapter bytes.
- Prepared profile:
  [`route-003-discovery-reliability-sonnet.json`](../../evals/profiles/route-003-discovery-reliability-sonnet.json).
- Purpose: remeasure the two positive discovery routes left inconclusive by Batch 1 after the
  roadmap's material-change trigger fired. This is measurement, not prompt tuning or promotion.

The exact candidate is deliberately the preceding committed revision. After approval, execute from
a clean detached checkout of that revision and pass the approved profile by absolute path. That
keeps `--require-clean-plugin` meaningful while allowing the separately committed approval record
to remain outside the measured plugin bytes.

## Fixed conditions

| Field | Approved value requested |
|---|---|
| Engine | native Claude plugin runner |
| Requested model | `sonnet` (resolved model recorded per trial; a mixed resolved-model batch is inconclusive) |
| Scenario 1 | `discovery-agent-authoring-workflow-graph` |
| Scenario 1 threshold | `0.66`, which is 2 of 3 planned trials |
| Scenario 2 | `discovery-service-readiness-audit` |
| Scenario 2 threshold | scenario default `1.0`, which is 3 of 3 planned trials |
| Trials | 3 per scenario; 6 live calls maximum |
| Per-trial timeout | 600 seconds |
| Total timeout | 7,200 seconds |
| Currency ceiling | USD 4.00, checked at one-trial granularity when the CLI reports trustworthy cost |
| Candidate cleanliness | `--require-clean-plugin` |
| Attempts | one batch; no retry, tuning, threshold change, or replacement candidate |

The profile claims candidate integrity, native plugin load, native target invocation, the bounded
routing-only behavioral contract, and deterministic grader outcome. Discovery remains byte-for-byte:
no required reference is injected into either prompt.

## Stop and retention rules

1. Do not start while profile approval is null or if the approved candidate, model, trials,
   timeouts, scenarios, thresholds, or budget differs from this packet.
2. Stop on candidate/plugin-input drift, authentication failure, total-time expiry, cost ceiling,
   unavailable cost after cost was expected, mixed resolved models, or runner integrity failure.
3. Retain `PASS`, `FAIL`, timeout, and `INCONCLUSIVE` outcomes as the one authorized measurement.
   Do not retry unchanged bytes merely to replace a timeout or red result.
4. A red or inconclusive batch does not authorize a description, prompt, scenario, grader, split,
   or threshold edit. Any repair needs a separately accepted fleet failure and candidate budget.
5. Before closure, rerun the unpaid deterministic overlap checks (`run_evals.py --validate`,
   `test_graders.py`, generator check, and Gate A). They prove suite integrity, not native routing.

## Executed command

From a clean detached checkout of the exact candidate:

```powershell
python evals/run_evals.py --run --profile <ABSOLUTE_APPROVED_PROFILE_PATH> --results-dir .eval-runs/route-003 --require-clean-plugin
```

The resulting sealed summary and `eval-result-envelope-v1.json` must be captured through
`scripts/capture_measurement_evidence.py` before any closure claim.

## Consumed approval

The owner authorized Sonnet execution within the per-item call ceiling. Commit `82fb2784` recorded
approver `latent-sre`, UTC `2026-08-31T04:50:47Z`, and budget ID
`route-003-discovery-reliability-2026-08-31` in the profile. The executed values were:

> I approve ROUTE-003 profile `route-003-discovery-reliability` for exact candidate
> `38dbdf70722c2167ce2c404297ccb4ccc3f5da8f`, requested model `sonnet`, three trials for each of the
> two named scenarios (six calls maximum), 600 seconds per trial, 7,200 seconds total, and USD 4.00
> maximum. Budget ID: `route-003-discovery-reliability-2026-08-31`.

That approval was consumed by the one terminal batch. A replacement requires a new explicit packet
and must not rewrite, overwrite, or discard the retained INCONCLUSIVE evidence.
