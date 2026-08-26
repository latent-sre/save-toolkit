# GRAPH-001, GRADER-003, and EVIDENCE-001 closure

> **Status: accepted closure evidence.** This packet records the base implementation and fresh
> verification for revision `d5c3189f93f53d96a4f656279e27a48c7b1a4316`, plus review hardening
> through exact PR head `1875057096ee94655821358117357922339ad015`, merged at `810f7e6`. Owner
> acceptance keeps the three direct scenarios in `calibration`.

## Conclusion

The three roadmap items closed on one accepted implementation line:

- `EVIDENCE-001` automatically writes a bounded durable record after an eval summary is sealed,
  provides the same capture path for host-owned exercises, and makes an unresolved live-roadmap
  batch identity a Gate A failure.
- `GRAPH-001`'s nine current, non-outdated PR #165 review findings were either fixed by the accepted
  implementation line or independently verified as already fixed on current `main`.
- `GRADER-003`'s direct-contract graders reject the reproduced false positives and accept the
  bounded semantic forms from three independent clean-context Terra trials. The deterministic
  transfer moved from 1/9 to 9/9 without weakening the retained adversarial fixtures.

PR #165 is `[verified live]` merged at `5d94987e37f6b9c9d4fd0f5427ea2269dab36131`.
Its review API exposed 13 unresolved threads at the time of the base candidate: four outdated and
nine current. The implementation addressed the nine current findings without rewriting that
historical review state. PR #176's six follow-up review threads were replied to and resolved on
exact head `1875057` before merge.

## EVIDENCE-001

The pre-tooling producer inventory and retention boundary are recorded in
[`2026-08-26-evidence-001-capture-design.md`](2026-08-26-evidence-001-capture-design.md).

Implementation:

- [`capture_measurement_evidence.py`](../../scripts/capture_measurement_evidence.py) validates and
  exclusively writes bounded eval or exercise evidence under `docs/reviews/`.
- [`run_evals.py`](../../evals/run_evals.py) seals the private summary, then requires durable
  capture before the batch can be published as a result.
- [`check_evidence_refs.py`](../../scripts/check_evidence_refs.py) resolves every eval-style batch ID
  cited by the live roadmap to committed Markdown evidence; Gate A runs it as a structural step.
- Raw stdout/stderr, prompts, tool payloads, full responses, session IDs, temporary paths, and
  credentials remain outside the durable record.

Red-to-green evidence: the two new test modules initially failed at import because neither capture
module existed. After implementation, both focused suites pass 3/3; the eval-runner suite passes,
including capture failure as a non-publishable runner failure.

## GRAPH-001 review dispositions

| Current PR #165 finding | Disposition on current candidate | Focused evidence |
|---|---|---|
| Preserve byte-valued timeout output | `worked` — decode with UTF-8 replacement before writing; retain `UNKNOWN` metadata | `test_timeout_is_unknown_and_retry_refuses_reuse` |
| Synchronize the standalone guard launcher | `already worked on main` — inlined and standalone launchers byte-match | `test_hook_wiring.py` and `test_fleet_doctor.py` green |
| Reject retry after inconclusive readback | `worked` — retry requires a safe terminal readback showing old, unchanged, or not executed | exact negative fixture in `test_production_unknown_outcome_relationships` |
| Require affirmative reconciliation ownership | `worked` — reject negated/unavailable ownership and require an owner relationship | exact negative fixture in `test_production_unknown_outcome_relationships` |
| Make the PATH assertion platform-neutral | `already worked on main` | incident-drill harness green on the current tree |
| Reject an empty successful lane result | `worked` — record `FAILED/EMPTY_RESULT`, omit result Markdown, return nonzero | `test_empty_success_result_is_a_failed_attempt` |
| Record post-reservation setup/launch failures | `worked` — record `FAILED/SETUP_OR_LAUNCH` and return nonzero | `test_setup_failure_after_reservation_is_recorded` |
| Constrain report run IDs to one component | `worked` — reject absolute paths, separators, `.` and `..` | `test_report_rejects_run_ids_that_escape_the_runs_root` |
| Reject a claim that the agent ran production reconciliation | `worked` — the production scenario now uses the relationship grader | `test_production_unknown_result_rejects_agent_reconciliation_claim` |

The canonical incident-drill changes were regenerated once into the Copilot projection. The
launcher remains an evidence harness, not an OS sandbox; the existing disposable,
credential-free-runtime boundary is unchanged.

## GRADER-003 Terra transfer

Three independent `gpt-5.6-terra` prompt-engineer trials answered the three direct prompts without
repository or grader access. The retained baseline is
[`2026-08-26-exercise-terra-grader-transfer-baseline.md`](2026-08-26-exercise-terra-grader-transfer-baseline.md):
eight of nine semantically complete responses were rejected by vocabulary-shaped graders. The
bounded transfer forms derived from those responses are frozen in `evals/test_graders.py`.

On exact implementation revision `d5c3189f93f53d96a4f656279e27a48c7b1a4316`, all nine transfer
forms pass and all reproduced oracle-gap negatives still reject. The candidate record is
[`2026-08-26-exercise-terra-grader-transfer-candidate.md`](2026-08-26-exercise-terra-grader-transfer-candidate.md).

No Claude eval batch was run. No repository harness result is relabelled as Terra: the current paid
harness is Claude-specific. This is a direct-prompt Terra transfer exercise plus deterministic
grader replay, sufficient for exact-revision calibration review but not automatic promotion.

## Fresh verification

| Command | Result |
|---|---|
| `python evals/test_graders.py` | 884/884 checks passed |
| `python evals/run_evals.py --validate` | 107 scenarios valid: 31 direct, 76 discovery |
| `python scripts/run_component_tests.py` | 31/31 suites passed; 0 quarantined |
| `python scripts/generate_platform_adapters.py --write` | 185 adapter files generated; byte validation passed |

Gate A, strict plugin validation, and final diff hygiene are run on the final documentation tree at
the push boundary and recorded in the pull request.

## Owner acceptance

On 2026-08-26, `latent-sre` accepted the merged `GRAPH-001` and `EVIDENCE-001` implementations and
closed `GRADER-003` while explicitly retaining its three direct scenarios in `calibration`. The 9/9
Terra transfer remains bounded semantic evidence; it is not relabelled as native Claude behavior or
used as independent promotion authority.
