# Complex campaign preparation evidence

This is preparation evidence for EVAL-012, not benchmark performance or candidate acceptance.
The live status remains in the [roadmap](../fleet-roadmap.md#eval-012--plan-incident-and-coding-evaluations-for-the-fleet).
The [implementation plan](../fleet-evaluation/implementation-complex-campaigns.md) preserves the full
WP-08/04/05/09 and campaign-report scope. No model, provider, real Docker or live cloud execution was
performed during this preparation. Public pinned source and optional SDK dependencies were fetched;
the two optional benchmark environments were installed only in ignored isolated directories.

## Prepared scope

| Requirement | Local evidence | Remaining execution/acceptance boundary |
|---|---|---|
| WP-08 complex repair cases | [Ten hard cases](../fleet-evaluation/wp08-complex-proposal.md), eight repositories, original full-row hashes and per-base licence hashes; separate v2 proposal and execution rejection while unaccepted | Owner accepts the changed selection/recipe; exact Linux CLI and image identities; hard-quota smoke on the selected Windows Docker Desktop host; bounded paid trials |
| WP-08 result integrity | Original supported PASS/FAIL survives later cleanup, billing or proxy failure; original verifier cleanup and later host recovery retained; batch stops and unresolved resources block reuse | Actual host containment and task execution remain unmeasured |
| WP-04 recorded incidents | [Five source-supported proposals](../fleet-evaluation/wp04-case-review.md), pinned observable-only fixtures, original evaluator export and separate exact local metrics | Exact case/observation-profile admission, native Windows read isolation, candidate/model/budget and original LLM judge acceptance |
| WP-05 conversations | [18 profiles over six families](../../evals/incident-conversations/README.md): twelve paired two-message cases, two six-message profiles and four branching profiles; real resume, shared CLI-turn budget and then-visible replay contexts | Human semantic case review; actual model/helper execution and bounded run acceptance; INC-05/06 remain held out |
| WP-09 reproduction | [Five hard SWT-compatible cases](../fleet-evaluation/wp09-swt-run-plan.md), original patch-role preservation, test-only admission, six independent variants, executable smoke and v1 mapping | Pinned compatible images and actual Windows/Docker smoke; exact owner acceptance and human test relevance |
| WP-09 terminal tasks | [Five complex Terminal-Bench adaptations](../fleet-evaluation/wp09-terminal-runplan.md), real pinned Harbor SDK, static author, stopped-author artifact transfer and fresh independent verifier | Reviewed digest-pinned/preseeded images, per-case smoke, exact candidate/model/spend and post-trial policy review |
| Campaign report | [Read-only report](../fleet-evaluation/campaign-report.md), selected-slot coverage, all-attempt costs, original verdicts, late errors and separate semantic/policy/cleanup dimensions | Reports evidence only; no automatic acceptance, credential-disablement claim or promotion |

[verified] WP-08 uses ten cases rated 1–4 or >4 hours upstream, selected before model results. Its
cases and SWT's five 1–4-hour cases are disjoint. The original easy-draw algorithm remains available
and unchanged. The complex proposal stays `pending-human-acceptance`; no acceptance field was set.

[verified] WP-04's revised selection is Scenario-7/21/24/80/102. It preserves 458 original assets
(441,911,602 raw bytes) in native fixtures totalling 499,755,899 bytes, below the declared 512 MiB
cap. Source inconsistencies, unavailable observations and exclusions are explicit in its packet.
Scenarios 29, 31 and 105 were excluded without repairing upstream truth. Full selected files are
retained; no answer-guided row excerpts or invented aliases are candidate inputs. The upstream
LLM assessment remains unmeasured; deterministic entity/edge arithmetic is a labelled adaptation.

[verified] WP-05's saved synthetic controls retain good PASS, bad FAIL, unavailable-branch structural
PASS and helper-event structural PASS across two rescoring passes, with no verdict differences.
These are subprocess/runner controls. They establish neither real model advice nor actual native
delegation. The report reads those saved v1 bundles and prints `semantic: UNVERIFIED` separately.

[verified] SWT uses the pinned upstream loader, six-variant generation, scripts, parser and grader
with Docker boundaries doubled in offline controls. Its Unix-only build/lock/resource imports are
guarded on Windows; reaching an unsupported operation raises rather than pretending to enforce it.
Harbor uses the actual pinned SDK factory, task parser and verifier APIs in its isolated environment.
The compressor's reference encoder is excluded from author staging because the original Dockerfile
does not copy it into the task workspace. Terminal adaptations retain original task IDs and rewards.

## Review and regression repairs

Independent source reviews covered the native/report/WP-08, WP-04 and WP-09 surfaces. The following
issues were reproduced and repaired before final integration:

- Campaign costs discarded known judge-call subtotals when the complete judge cost was unknown,
  and rejected the native writer's six-decimal rounding. The report now preserves the recorded floor.
- Extra trial slots inflated selected coverage. Nine extra successful trials now leave a missing
  selected first trial at 0/1; their evidence and spending remain visible.
- SWT admission ignored retained smoke files. It now reopens digest-bound evidence before key access.
- Generic SWT smoke functions were not collected by Django's unittest runner. Compatible test classes
  are now used for Django, with module functions retained for pytest and SymPy. A follow-up caught
  that the class-only repair broke SymPy's custom collector; regressions now execute the collection
  loop from its exact selected base as well as Django's target-generation/discovery boundary.
- SWT publication dropped shared adapter identity. Admission, saved binding and v1 provenance now
  share one digest that includes shared code, SWT code and its dependency file.
- WP-04's Scenario-102 bindings included four unrelated load-generator resources in ad-service
  groups. Those entries were removed; all five binding sets were rebuilt from original metadata.
  The scorer now checks original kind/namespace/name/filter metadata itself. Anchored matching
  replaces substring matching, and wrong-downstream plus poisoned-binding controls cannot PASS.
  This changes the local metric identity to `wp04-exact-entity-edge-v2`; original upstream truth is unchanged.

## Verification

[verified] The final combined run used the managed Python 3.14.8 interpreter on clean committed
source `07d2b48d126ca6f62f18171f4529f5b98fafd87b`:

```text
/home/hawkfire/save-toolkit/.venv/bin/python scripts/local_tests.py --heavy
5113 passed, 89 skipped, 5056 subtests passed; exit 0 in 86.113 seconds
receipt: 20261025T121931Z-47972811
```

The receipt is under the common Git directory's `local-test-runs/`, with pytest output, JUnit and
runtime/revision metadata. Both before/after snapshots name that commit and a clean tree. The earlier
working-tree receipt `20261025T114711Z-3bdbd058` and clean-source receipt
`20261025T115754Z-983446d0` are retained as pre-review-repair history, not substituted for this final run. Subsequent evidence-document updates do not change the tested product or test code.

[verified] Targeted immutable source re-reviews closed all reported findings: report/WP-04 repairs
at `eb0be82e` and the final SWT framework repair at `152c255e`, reusing the unchanged earlier scopes.
A later automated PR review found three WP-09 issues, repaired and independently source-approved
at `07d2b48d`: failed proxy shutdown now remains in cleanup evidence and blocks Harbor reuse; SWT
leaves author test execution unknown pending policy review; SWT and the shared WP-08 binding refuse
elevated or unknown host accounts before Docker access. Red/green regressions cover each path.
Those were source reviews; test execution evidence belongs to the named runs, not the reviewers.

[verified] Ruff check, Ruff format check (61 files), strict mypy (68 source files), `git diff --check`
and Gate A passed. The native catalog validates 399 scenarios. New Python modules are registered
in the shared lint/type scopes; optional SWT/Harbor dependencies retain exact isolated-environment pins.

[verified] Optional upstream integration evidence supplements the default environment's skips:
the isolated Harbor SDK suite passed 71 checks; its seven owned-lifecycle/report checks passed again
after the campaign-report repairs. After the later PR repairs, all 18 real-SDK checks passed,
including unresolved-proxy cleanup and refusal of a second attempt before credential access.
Four SWT controls exercised the actual pinned upstream code with
Windows import guards active and Docker boundaries doubled. These are API/runner checks, not live
task executions. Focused repair checks include 54 ITBench tests, 54 SWT tests and 60 combined
report/comparison checks. The 89 full-suite skips include unavailable optional dependencies and
platform paths; they are not counted as passes.

## Evidence limits

[unverified] No live benchmark result, working Windows/Docker quota, image/cache compatibility,
model availability, provider bill, human semantic acceptance or candidate promotion follows from
these offline checks. The operator plans contain executable smoke commands and explicit subsequent
owner gates. A correct static-authoring refusal is separate from task outcome; source test rewards
do not establish policy compliance. Eval results never promote a candidate.
