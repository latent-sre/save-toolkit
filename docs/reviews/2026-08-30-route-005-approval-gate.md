# ROUTE-005 paired native discovery approval gate

> **Status:** `[verified static]` One minimal description candidate is committed and the paired
> incumbent/candidate profiles validate offline. **Human gate:** both profiles intentionally carry
> `"approval": null`; no live model call or spend is authorized.

## Exact adjacent revisions

| Arm | Exact revision | Description posture |
|---|---|---|
| Incumbent | `54444fcdbafc52790af4e4d8eede1c12460c93b7` | abstract fleet-language triggers |
| Candidate | `6e2d1c9f6cb2780144b221ec0071977039e1b615` | on-call trigger phrasings from the retained prompt openings |

The revisions are adjacent. Their entire diff is the same four folded-description lines in the
canonical `incident-investigation` skill and its generated Copilot projection. The capability lead
and all exclusions are unchanged. The candidate description is 548 UTF-8 bytes, retains literal
`Triggers:`, and remains below the 600-byte ceiling.

The one candidate replaces only:

- `what incident mode is this` with `prod just paged me; what do I check first`;
- `is first response still enough` with
  `I am on-call; help me build the differential between these causes`; and
- `does this need systemic analysis` with
  `the spike is over but services are still degraded`.

This is a robustness candidate, not a defect repair. The incumbent already routed the three named
scenarios in the prior clean-room evidence; response-grader reds in that evidence are not routing
failures and are not a reason to tune the description.

## Fixed paired conditions

Both arms use comparison ID `route-005-incident-investigation-paired` and the same engine-neutral
comparison digest `7f4ef7e60761936acae16c1bbdb86d7693e9081bcc47eea064aa194f4d0085b0`.

| Field | Value per arm |
|---|---|
| Engine | native Claude plugin runner |
| Requested model | `sonnet` (resolved model recorded per trial; mixed models make the batch inconclusive) |
| Scenarios | `discovery-incident-investigation-first-response`, `discovery-incident-investigation-systemic-failure`, `discovery-incident-investigation-defers-engineering-altitude` |
| Thresholds | each scenario's declared/default full threshold; 3 of 3 per scenario, including the `not_fire` negative |
| Trials | 3 per scenario; 9 calls per arm; 18 calls aggregate maximum |
| Per-trial timeout | 600 seconds |
| Total timeout | 7,200 seconds per arm |
| Currency ceiling | USD 4.00 per arm; USD 8.00 aggregate maximum |
| Candidate cleanliness | `--require-clean-plugin` in separate clean detached worktrees |
| Attempts | one incumbent batch and one candidate batch; no tuning, retry, or replacement candidate |

Prepared profiles:

- [`candidate`](../../evals/profiles/route-005-incident-investigation-candidate-sonnet.json)
- [`incumbent`](../../evals/profiles/route-005-incident-investigation-incumbent-sonnet.json)

The profiles contain no reference injection because discovery prompts must remain byte-for-byte.

## Stop, comparison, and retention rules

1. Do not start either arm until both exact revisions and both profiles are approved with distinct
   budget IDs. One approved arm without the other is not a comparable result.
2. Stop the affected arm on revision/plugin drift, authentication failure, total-time expiry, its
   USD 4 ceiling, unavailable cost after cost was expected, mixed resolved models, or runner
   integrity failure. Do not silently substitute a later revision.
3. Retain every `PASS`, `FAIL`, timeout, and `INCONCLUSIVE` result. Do not rerun unchanged bytes to
   manufacture a complete pair or a preferred winner.
4. Adopt the candidate only if it preserves all three routing outcomes without a safety, authority,
   or negative-route regression. A tie is expected evidence for robustness and does not imply the
   incumbent was defective.
5. A red content grader is analyzed separately from target invocation. It does not authorize
   prompt, description, grader, threshold, or split edits under this packet.

## Commands after explicit approval

Run the profiles from separate clean detached worktrees at the two bound revisions, passing each
approved profile by absolute path:

```powershell
python evals/run_evals.py --run --profile <ABSOLUTE_CANDIDATE_PROFILE_PATH> --results-dir .eval-runs/route-005-candidate --require-clean-plugin
python evals/run_evals.py --run --profile <ABSOLUTE_INCUMBENT_PROFILE_PATH> --results-dir .eval-runs/route-005-incumbent --require-clean-plugin
```

Capture both sealed result envelopes through `scripts/capture_measurement_evidence.py` before any
adoption or closure claim. Then rerun the unpaid scenario, grader, generator, and Gate A checks.

## Approval text needed

A sufficient owner authorization is:

> I approve the ROUTE-005 paired comparison of exact incumbent
> `54444fcdbafc52790af4e4d8eede1c12460c93b7` and exact candidate
> `6e2d1c9f6cb2780144b221ec0071977039e1b615`, requested model `sonnet`, the three
> named scenarios at three trials each, 600 seconds per trial, 7,200 seconds per arm, USD 4.00 per
> arm and USD 8.00 aggregate. Candidate budget ID:
> `route-005-incident-investigation-candidate-2026-08-30`; incumbent budget ID:
> `route-005-incident-investigation-incumbent-2026-08-30`.

Until that approval is received and recorded with UTC timestamps, ROUTE-005 remains at the human
gate and neither live command runs.
