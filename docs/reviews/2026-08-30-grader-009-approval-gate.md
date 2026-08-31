# GRADER-009 paired historical/current native remeasurement gate

> **Status:** `[verified static]` Both phrasing repairs are committed. The two Sonnet profiles carry
> owner approval recorded at `2026-08-31T11:44:14Z`; the two Opus profiles have approval `null`.
> No GRADER-009 cell has started. The fixed matrix cannot start until Opus is explicitly authorized
> and the subscriber OAuth session is refreshed.

## Exact revisions and evaluator boundary

| Arm | Exact plugin revision | Evaluator/scenario bytes |
|---|---|---|
| Historical incumbent | `2cdcbbbac3bc560076a1d0c648149173b6863602` | current campaign evaluator copied into an isolated detached worktree |
| Current candidate | `6e90d06e27acda01cbaa404fc65528a8bdb20625` | current campaign evaluator in its native checkout |

Repair commits `f9075751` (both named grader fixes) and `ff7a6293` (follow-up hardening) are ancestors
of the current candidate. The historical arm deliberately uses the current scenarios and grader
bytes: it measures the old plugin response against the repaired oracle, rather than comparing two
different rulers.

For the historical cells, copy only the current `evals/` tree into the isolated historical
worktree. Do not copy current agents, skills, commands, hooks, or generated adapters. The overlay
makes the historical workspace dirty by design, but `plugin_inputs_dirty` must remain false and
`--require-clean-plugin` must pass. The evidence must record both that dirty-workspace fact and the
current eval-suite digest; neither may be relabelled as a fully clean historical checkout.

## Four fixed cells

| Cell | Scenario | Model | Trials | Per-trial / total timeout | USD ceiling |
|---|---|---|---:|---:|---:|
| current handoff | `agent-direct-observability-engineer-defers-live-incident` | `sonnet` | 3 | 600 / 2,400 s | 2.00 |
| incumbent handoff | `agent-direct-observability-engineer-defers-live-incident` | `sonnet` | 3 | 600 / 2,400 s | 2.00 |
| current unknown write | `agent-direct-observability-engineer-unknown-write-outcome` | `opus` | 3 | 900 / 3,600 s | 4.00 |
| incumbent unknown write | `agent-direct-observability-engineer-unknown-write-outcome` | `opus` | 3 | 900 / 3,600 s | 4.00 |

Each unchanged scenario has the default 1.0 threshold, so its cell requires 3 of 3 planned trials.
The campaign maximum is 12 calls and USD 12.00. Sonnet is retained for the observed particle-form
handoff sentence; Opus is retained for the observed quoted-warning false positive. Models are not
substitutable between cells.

Prepared profiles:

- [`current handoff`](../../evals/profiles/grader-009-defers-current-sonnet.json)
- [`incumbent handoff`](../../evals/profiles/grader-009-defers-incumbent-sonnet.json)
- [`current unknown write`](../../evals/profiles/grader-009-unknown-current-opus.json)
- [`incumbent unknown write`](../../evals/profiles/grader-009-unknown-incumbent-opus.json)

The two handoff profiles share engine-neutral comparison digest
`6409eb19a51150fcaf3c47202d601726a146f36fba83476a9db59d62971108ec`; the two unknown-write
profiles share `88648804ad5d841f3ae913c2efd23c1130769a7415f2735f560f17eb92203550`.
No profile injects a reference or changes the direct prompt.

## Stop, comparison, and retention rules

1. Each cell requires its own explicit approval and budget ID. Approval of one revision, scenario,
   or model does not authorize another cell. Do not start the campaign unless all four cells are
   approved as one fixed matrix.
2. Stop the affected cell on revision/plugin drift, authentication failure, total-time expiry, its
   cell ceiling, unavailable expected cost, mixed resolved models, or runner integrity failure.
3. Retain every `PASS`, `FAIL`, timeout, and `INCONCLUSIVE` result. Do not rerun an incomplete or red
   cell, and do not tune either grader from the new responses.
4. Report target invocation separately from deterministic content grading. In the handoff scenario,
   the old measured response also missed legitimate after-the-fact work; repairing one false red
   does not rewrite that genuine failure.
5. Compare only like-model, like-scenario cells with matching comparison digests. Do not aggregate
   Sonnet and Opus into one success rate.

## Commands after explicit approval

Run each profile from the matching worktree and pass the separately approved profile by absolute
path:

```powershell
python evals/run_evals.py --run --profile <CURRENT_HANDOFF_PROFILE> --results-dir .eval-runs/grader-009-current-handoff --require-clean-plugin
python evals/run_evals.py --run --profile <INCUMBENT_HANDOFF_PROFILE> --results-dir .eval-runs/grader-009-incumbent-handoff --require-clean-plugin
python evals/run_evals.py --run --profile <CURRENT_UNKNOWN_PROFILE> --results-dir .eval-runs/grader-009-current-unknown --require-clean-plugin
python evals/run_evals.py --run --profile <INCUMBENT_UNKNOWN_PROFILE> --results-dir .eval-runs/grader-009-incumbent-unknown --require-clean-plugin
```

Capture all four sealed summaries and result envelopes through
`scripts/capture_measurement_evidence.py` before any closure claim. Then rerun `test_graders.py`,
`run_evals.py --validate`, generator check, and Gate A on the current branch.

## Approval contract (partially satisfied)

A sufficient authorization is:

> I approve the GRADER-009 four-cell matrix comparing exact historical plugin
> `2cdcbbbac3bc560076a1d0c648149173b6863602` with exact current plugin
> `6e90d06e27acda01cbaa404fc65528a8bdb20625`, using the current evaluator: Sonnet x3 per revision
> for `agent-direct-observability-engineer-defers-live-incident` at 600 seconds/trial and USD 2.00
> per cell; Opus x3 per revision for `agent-direct-observability-engineer-unknown-write-outcome` at
> 900 seconds/trial and USD 4.00 per cell; 12 calls and USD 12.00 aggregate maximum. Budget IDs:
> `grader-009-defers-current-2026-08-30`, `grader-009-defers-incumbent-2026-08-30`,
> `grader-009-unknown-current-2026-08-30`, and `grader-009-unknown-incumbent-2026-08-30`.

The two Sonnet approvals are recorded. The two Opus approvals are not; the fixed matrix therefore
remains unstarted. Even after Opus authorization, it must run as one campaign only after a fresh
authentication check succeeds. Neither partial approval nor a failed authentication check
authorizes a partial matrix, model substitution, tuning, or retry.
