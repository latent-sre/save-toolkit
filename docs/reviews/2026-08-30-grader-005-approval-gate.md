# GRADER-005 native frontend posture remeasurement gate

> **Status:** `[verified static]` The code-side grader repair is an ancestor of the exact candidate
> and the native execution profile validates offline. **Human gate:** the profile intentionally
> carries `"approval": null`; no live model call or spend is authorized.

## Exact candidate and settled repair

- Exact candidate: `54f1c8d0ddbc17545f644fdd2568a36c8471454c`.
- `dcf7852f` (`gate_posture` and its red-first controls) is an ancestor of the candidate.
- `7c92c5ac` (later `gate_posture` hardening) is also an ancestor.
- Prepared profile:
  [`grader-005-frontend-posture-sonnet.json`](../../evals/profiles/grader-005-frontend-posture-sonnet.json).

The offline repair is not being redesigned here. `gate_posture` distinguishes an affirmative merge
block/prerequisite from replies that merely name the owed rule while saying they are not blocking
the merge. Existing blocking fixtures pass; the retained no-skill pressure controls remain red.
The only open acceptance step is native remeasurement on committed bytes.

## Fixed conditions

| Field | Approved value requested |
|---|---|
| Engine | native Claude plugin runner |
| Requested model | `sonnet` (resolved model recorded per trial; mixed models make the batch inconclusive) |
| Scenarios | `discovery-frontend-craft-blocks-mantine-tailwind`, `discovery-frontend-craft-framework-evidence`, `discovery-frontend-craft-render-is-not-verification` |
| Thresholds | each scenario's unchanged default `1.0`; 3 of 3 planned trials |
| Trials | 3 per scenario; 9 calls maximum |
| Per-trial timeout | 600 seconds |
| Total timeout | 7,200 seconds |
| Currency ceiling | USD 4.00, enforced at one-trial granularity when trustworthy cost is reported |
| Candidate cleanliness | clean detached checkout plus `--require-clean-plugin` |
| Attempts | one batch; no retry, prompt/description edit, grader tuning, or threshold/split change |

Discovery prompts remain byte-for-byte and no reference is injected. Target invocation and
response-grader verdicts must be reported separately: a routing miss is not a posture-grader defect,
and a content red is not permission to tune the route.

## Stop and retention rules

1. Do not start until the owner approves the exact candidate, profile, requested model, scenarios,
   trials, timeouts, and USD ceiling under one budget ID.
2. Stop on candidate/plugin drift, authentication failure, total-time expiry, the USD 4 ceiling,
   unavailable expected cost, mixed resolved models, or runner integrity failure.
3. Retain `PASS`, `FAIL`, timeout, and `INCONCLUSIVE` outcomes from the one batch. Do not retry
   unchanged bytes to replace a red or incomplete sample.
4. A red does not authorize another grader edit. First classify target invocation, evaluate the
   retained response against the already pinned controls, and return any proposed change to a new
   red-first owner decision.

## Command after explicit approval

From a clean detached checkout of the exact candidate, with the separately approved profile passed
by absolute path:

```powershell
python evals/run_evals.py --run --profile <ABSOLUTE_APPROVED_PROFILE_PATH> --results-dir .eval-runs/grader-005 --require-clean-plugin
```

Capture the sealed summary and result envelope through `scripts/capture_measurement_evidence.py`
before any closure claim, then rerun `test_graders.py`, `run_evals.py --validate`, generator check,
and Gate A.

## Approval text needed

A sufficient authorization is:

> I approve GRADER-005 profile `grader-005-frontend-posture` for exact candidate
> `54f1c8d0ddbc17545f644fdd2568a36c8471454c`, requested model `sonnet`, the three named scenarios
> at three trials each (nine calls maximum), 600 seconds per trial, 7,200 seconds total, and USD
> 4.00 maximum. Budget ID: `grader-005-frontend-posture-2026-08-30`.

Until that approval is received and recorded with a UTC timestamp, GRADER-005 remains at the human
gate and no live command runs.
