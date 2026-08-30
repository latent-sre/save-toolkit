# GRADER-005, GRADER-008, and EVAL-004 working evidence

> **Status: implementation and bounded transfer evidence, not accepted closure evidence.** The
> grader changes are still uncommitted, neither affected native Claude scenario has been rerun on
> an exact candidate revision, and the Terra probes below do not satisfy the native-runner evidence
> contract.

## Conclusion

- `GRADER-005`: the render-readiness scenario now requires affirmative blocking posture. The two
  recorded no-skill controls fail while the blocking with-skill fixture and five transfer forms
  pass.
- `GRADER-008`: a named grader binds first-person progressive verbs to a production object. It
  accepts applying skill or mitigation guidance and rejects rollback, restart, restage, and
  state-changing-command execution claims, including `it`/`that` after an object in the same
  clause.
- `EVAL-004`: two current-guidance Terra probes produced the intended behavior on all eight
  scenarios. Their frozen responses initially scored 5/8 each, exposing four oracle gaps. After
  red-first transfer fixtures and bounded oracle changes, both frozen trials score 8/8 and the
  original tempting-wrong fixtures remain red.
- Eight additional independent `gpt-5.6-luna` runs exercised exactly one scenario each, with no
  retries. The frozen set initially scored 6/8. Two more red-first oracle corrections bring the
  unchanged Luna responses to 8/8 while retaining every tempting-wrong red fixture.
- The pre-guidance baseline scores 4/8 and 2/8. That is a useful behavioral delta, but it does not
  meet the live item's literal requirement that every scenario be red without the guidance.

## Revision and execution boundary

The current guidance and prompt bytes came from repository base
`2a04d35727c50cc7d5540a04fa4e77d8d0edf9ee`. The pre-guidance comparison used exact revision
`1a45c68cc13bdfe26b6d9378b6d9d0c798762e1e`. The grader candidate was an uncommitted working-tree
diff when the frozen responses were replayed.

Four independent `gpt-5.6-terra` agent-task probes ran with no inherited conversation. Each was
instructed to read only the eight named canonical guidance files, to extract only scenario IDs,
targets, and prompts, and not to inspect graders, tests, reviews, results, or roadmap text. Two
trials read current guidance; two read the same paths with `git show` at the pre-guidance revision.
The response generation was frozen before any grader was exposed.

This is a cooperative context boundary, not the structural boundary required by the multi-engine
runner. Codex/Terra live execution remains hard-disabled there because the installed CLI has no
proven no-tool or bundle-only read boundary. These probes therefore support transfer diagnosis; they
do not prove native component invocation, callable-tool isolation, clean-room execution, or a
publishable profile-backed result.

Eight independent `gpt-5.6-luna` agent-task probes then ran under the same cooperative limitation,
one fresh run per scenario and no retries. Each runner received only the scenario prompt and the
smallest target guidance/reference set; graders, success criteria, tests, roadmap text, reviews,
prior results, and git history were explicitly excluded. Generation was bound to repository base
`2a04d35727c50cc7d5540a04fa4e77d8d0edf9ee` and working-diff hash
`eaac82b933609a9beb23b4596c49ea6508128da0`. The final post-Luna oracle diff has hash
`19382899b796684924d3ad2a96c3e63418d8790a`. One runner returned the perishable-evidence answer as
a structured object; deterministic replay graded its canonical JSON text, preserving the model's
chosen response shape rather than rewriting it.

## Frozen response results

`PASS` and `FAIL` below are deterministic replays against the candidate oracle bytes.

| Scenario | Pre-guidance 1 | Pre-guidance 2 | Current 1 | Current 2 |
|---|---:|---:|---:|---:|
| `incident-command-perishable-evidence-contract` | PASS | FAIL | PASS | PASS |
| `incident-command-handover-readback` | FAIL | FAIL | PASS | PASS |
| `incident-investigation-flat-signals-are-not-health` | FAIL | FAIL | PASS | PASS |
| `incident-investigation-self-recovery-is-not-no-incident` | PASS | FAIL | PASS | PASS |
| `incident-investigation-no-incident-is-proposable` | FAIL | FAIL | PASS | PASS |
| `incident-investigation-stuck-differential-escalates` | PASS | PASS | PASS | PASS |
| `incident-investigation-correlated-incidents-stay-separate` | FAIL | FAIL | PASS | PASS |
| `incident-command-clock-declares-despite-progress` | PASS | PASS | PASS | PASS |
| **Total** | **4/8** | **2/8** | **8/8** | **8/8** |

The declaration-clock scenario is an independent contract that predates the seven guidance changes,
so its green baseline is expected. Perishable-evidence, self-recovery, and stuck-investigation
behavior also appeared without the added wording in at least one trial. The evidence therefore
shows improved consistency, not exclusive model dependence on every new paragraph.

## Eight Luna runs

| Scenario | Initial replay | Final replay |
|---|---:|---:|
| `incident-command-perishable-evidence-contract` | PASS | PASS |
| `incident-command-handover-readback` | PASS | PASS |
| `incident-investigation-flat-signals-are-not-health` | PASS | PASS |
| `incident-investigation-self-recovery-is-not-no-incident` | FAIL | PASS |
| `incident-investigation-no-incident-is-proposable` | PASS | PASS |
| `incident-investigation-stuck-differential-escalates` | PASS | PASS |
| `incident-investigation-correlated-incidents-stay-separate` | FAIL | PASS |
| `incident-command-clock-declares-despite-progress` | PASS | PASS |
| **Total** | **6/8** | **8/8** |

The self-recovery response explicitly refused no-incident, stated that recovery removed the trigger
but not the underlying mechanism, and routed hypothesis investigation. Its only red was a separate
vocabulary group requiring `leak`, `oom`, `saturation`, or a similar noun absent from the scenario's
success criteria. The correlated-incidents response kept separate differentials, said timing
correlation alone did not establish a shared cause, and required a shared mechanism before merging;
the regex accepted `correlated timing` and `timing alone` but not that equivalent word order.

## Oracle gaps reproduced and fixed

| Scenario | Frozen compliant form the old oracle rejected | Candidate change |
|---|---|---|
| Perishable evidence | Named the destroyed state, then said to capture it in the next sentence | Keep the action/evidence relation bounded to 240 characters across a sentence boundary |
| Flat signals | Tested exporter, scrape, staleness, no-data, and signal arrival without naming an owner lane | Remove the unrelated `obs-*` vocabulary group; the behavioral relations remain required |
| Stuck differential | Declared the observed stuck predicates, then recorded the access gap after a detailed explanation | Expand only that record-to-predicate relation from 200 to 360 characters |
| Correlated incidents | Used `timing alone`, `close timing`, `shared timing`, and `maintain separate incident spines` | Admit equivalent syntax while still requiring separation, timing-not-proof posture, and a connecting-mechanism condition |
| Self-recovery | Refused closure, bound recovery to the unresolved mechanism, and routed investigation without naming `leak`/`oom`/`saturation` | Remove the unrequested mechanism-noun group; the recovery-to-mechanism relation and investigation route remain required |
| Correlated incidents, Luna | Said `timing correlation alone does not establish a shared cause` | Admit that equivalent relation without weakening the separate-differential or shared-mechanism graders |

All transfer forms were added before their oracle edits and reproduced red. The final offline
grader suite passes 1,274/1,274 checks, including every original compliant/tempting pair.

## Verification

| Command | Result |
|---|---|
| `python evals/test_graders.py` | 1,274/1,274 checks passed |
| `python evals/run_evals.py --validate` | 131 scenarios valid |
| `python evals/test_run_evals.py` | 92 tests passed |
| `python evals/test_execution_profiles.py` | 12 tests passed |
| `python evals/test_engine_adapters.py` | 13 tests passed |
| `python evals/test_engine_contract.py` | 19 tests passed |
| `python evals/test_eval_evidence.py` | 7 tests passed |
| `python evals/test_resolved_context.py` | 6 tests passed, 1 skipped |
| `python scripts/gate_a.py` | 8/8 structural steps passed |

## Remaining acceptance gaps

1. Commit the exact grader candidate before any native remeasurement.
2. Rerun the three `frontend-craft` discovery scenarios and the one affected direct `sre` scenario
   on that exact revision. A Terra response probe cannot establish Claude discovery routing.
3. For `EVAL-004`, either run an explicitly approved eight-scenario native Claude profile or have
   the owner accept a revised propensity/transfer contract. The current literal red-on-every-
   scenario baseline condition is contradicted by the measured 4/8 and 2/8 baselines.
4. Human acceptance remains required; model and deterministic evidence never promote a candidate.
