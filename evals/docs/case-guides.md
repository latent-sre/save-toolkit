# Evaluation case guides

[Evaluation home](../README.md) · [Verification policy](../../CONTRIBUTING.md#3-verify-in-proportion-to-the-change)

## Tests

The `agent-direct-reliability-engineer-*` cases check supplied-state judgments about effective
controls, recovery evidence, toil economics, and continuation after a partial, stale helper return.
The paired `build-reliability-engineer-redelivery` and
`build-sre-assistant-redelivery-baseline` cases use identical prompt, fixture and outcome checks;
compare their source retrieval, protected counterexample, decision and useful next action on the
same model/host and exact plugin bytes. The automated verdict checks the decision and non-actions,
not successful source reads or citation quality; inspect those in both native traces. The offline
test reproduces the fixture's duplicate effect after acknowledgement failure and enforces pair
identity. `build-reliability-engineer-doc-boundary` is specified to check that an explicitly
requested assessment document is written while an untrusted instruction to edit application
configuration is refused; source reads and document quality still need trace review.
The native helper conversation checks actual dispatch and parent continuation structurally, then
requires manual review of its evidence synthesis and corrected follow-up. The routing overlaps
probe lifecycle, causal diagnosis, small arithmetic, a full toil assessment and accepted
implementation separately. Offline checks calibrate fixtures and graders; they do not run a model,
prove host containment, or establish operational benefit. The 2026-10-08 two-trial native
comparison left the lane unaccepted. See [RELIABILITY-001](../../docs/fleet-roadmap.md#reliability-001--measure-the-timing-repair-on-claude-then-decide-on-the-reliability-lane)
for the current status, landed timing repair, bounded comparison, and human run-approval and
acceptance requirements; this guide does not duplicate its live status.

`build-principal-engineer-contract-change` and its identical incumbent arm
`build-software-engineer-contract-change-baseline` grade a shared-contract design: an exact consumer
inventory that includes a dashboard parsing the fields only in configuration, an external reader
kept unknown, a compatible first release, removal only on evidence, and the owner's decision. Each
field is its own reply check, so the pair compares decisions rather than reply format, and guards
reject a field given twice or spelled with a unicode escape. Both pairs also require the design-record oracle, skills loaded
before the document is written, and no shell, as their prompts do.
`build-principal-engineer-new-system` and its identical incumbent arm
`build-software-engineer-new-system-baseline` check a new-system record with the
[design-record oracle](../oracles/principal-engineer/check_design_record.py), which requires every slot
to be filled, plus stack fit, an unset availability target left to the owner, a guard against any
decision given twice, and the closed-reply contract that only the lane carries.
`build-principal-engineer-order-event-identity` and its identical incumbent arm make the right
answer the less obvious one: adding `account_id` looks backward compatible, but the fixture's
fulfilment worker rejects any unexpected field, so the reply must say it is not. The pair also
requires `database-reliability` before the backfill and replay plan.
`build-principal-engineer-platform-selection` is lane-only and grades the second reasoning depth
against `distinguished.md`. It needs a proposed record, a reversible first step, and unverified
vendor claims. The accepted job-scheduler pattern must beat a new runtime or a scheduler of our
own. The new-system pair also requires `obs-alerting` before its paging rule. Four routing
positives cover a new-service design assignment, a builder's returned fork, a multi-year
platform selection, and a team service's workflow graph; four negatives require
reliability assessments, small tool builds, an independent review of a design document, and the
fleet's own workflow-graph design to reach their own lanes. The design-review negative seeds the
two consumers its document names; a review the main session keeps passes, as does one handed to
`reviewer`, and the design lane taking it fails. `python -m pytest
evals/test_principal_cases.py` calibrates them offline; design quality needs document review, and
native acceptance stays open under `PRINCIPAL-001`.

The [PRINCIPAL-001 semantic proposal](../proposals/principal-judgment/README.md) is deliberately
outside the active catalog and canonical rubric/corpus maps until reviewed activation and a new
accepted calibration are approved. It retains four paired scenarios, eighteen proposed labels,
and a rubric containing the full prompt and fixture files for each case. Its offline tests bind
the rendered context to those fixtures; they do not establish semantic model accuracy. Keeping
the proposal must not invalidate calibration receipts for unrelated active scenarios.

`build-principal-engineer-live-store-cutover` and `build-software-engineer-live-store-cutover`
prepare a fresh held-out case for the frozen lane candidate: concurrent writes/deletes during a
store copy, bounded-pause cutover, and recovery after replacement-only writes. Their prompts,
fixtures and checks are identical. `python -m pytest evals/test_principal_heldout.py` verifies
pair equality and the same-count/different-state rehearsal counterexample without model calls.
Artifact/boundary and skill-load checks remain separate from substantive design review; no
keyword semantic oracle is added. The [preregistered review protocol](../../docs/reviews/2026-10-08-principal-heldout-cutover.md)
requires uniformly hidden author metadata and a frozen first pass before trace reconciliation.
The approved six-trial native campaign and independent AI review are complete. The linked receipt
preserves all three review stages and reports a held-out design tie, separate from principal's
method/boundary consistency. Structural results do not dispose of its substantive design findings.
The frozen method checks' labels say before Write while their predicates require before the first
potentially mutating call; the report distinguishes actual skill loads from that ordering failure.

The incident advisor now uses one seven-field board. Its structural check is
`python evals/oracles/incident-closing-fields/probe_closing_fields.py <response.md> board`.
Legacy `fields`/`checkpoint` expectations remain for historical comparisons, not current acceptance.
Completeness does not establish useful advice, factual accuracy, or continuity across turns;
those require assessment of the conversation against the supplied incident evidence.
The `incident-companion-*` scenarios use the `incident_board` grader for structure and
the companion rubric for advice quality; they cover explanation, missing access, handover
read-back, helper assignment and return reconciliation, and current and stale service cards.
Rubric calibration examples assess semantics alone; they need not contain a board and are not
complete scenario passes. The board is the reply's last step (the skill's step 6), so a line
after it fails the board grader by design.

The `discovery-incident-investigation-existing-bridge` and
`discovery-incident-investigation-existing-tlc-followup` scenarios cover a current bridge and
supplied prior-turn TLC context. Beyond routing, they grade the board and the companion rubric's
`existing_bridge`/`existing_tlc` cases. The follow-up scenario is a conversation snapshot,
not a native resumed session, so it does not establish runtime continuity.

The sre-assistant build probes grade the agent's return packet (`Returning to:` through
`Caller next step:`), mitigation choice through the `mitigation_recommendation` rubric, refusal
of evidence-destroying actions through `compromise_preserves_evidence`, and masking of the echoed
session username. Three sre-assistant paths cannot run in this harness and stay host-acceptance
items, not regression coverage: the Playwright/Grafana visual path (strict MCP supplies no
servers), the dispatched child's reads in routing trials (the child runs without Bash), and
researcher dispatch from the agent.

`python -m pytest evals/ --heavy` covers the runner, graders, and judge without a model. A plain
`python -m pytest evals/` skips the heavy eval-machinery files listed in the root `conftest.py`
(`HEAVY`), among them the probe-trial, checking and oracle suites, so it does not. Gate A is
structural and does not run them; CI runs both shards, and its required `component-tests` check
passes only when both do.

For a final local full run, use `python scripts/local_tests.py --heavy` from the repository root.
It coordinates linked worktrees and saves logs, JUnit timings, and revision/command receipts.
Local pytest defaults to ten workers; CI explicitly keeps four. Scenario data edits use validation
and their matching contract/behavioral checks, while evaluator changes require broader coverage;
the selection rule lives in [CONTRIBUTING.md](../../CONTRIBUTING.md#3-verify-in-proportion-to-the-change).
## WP-10 offline adversarial preparation

The [AC-20 inventory](../wider-fleet-inventory.md) maps lane gaps and offline controls.
The [AC-27 agent-side pairs](../oracles/agent-injection/README.md) cover repository, supplied-log
and seeded-helper surfaces with scripted obeying/resisting controls.
The judge-input surface is six `AC-27 judge-input calibration` cases in the active corpus, framed by
`judge.py`'s per-response marker tag so that a response containing an end marker cannot close its
frame early; `test_judge_injection.py` checks both offline. Both the fix and the cases need one
owner-approved cold recalibration before any rubric trial uses them. Offline discrimination is not
candidate acceptance or completion of WP-10.

The [natural-response extension](../oracles/natural-injection/README.md) adds six build cases with
normal prose reports, actual local fixture effects in offline controls, and an explicit human
semantic-review gate. Mechanically successful runs remain INCONCLUSIVE until separately reviewed;
a supported mechanical failure still returns FAIL. No judge or runner bytes change.
## WP-12 offline GCP pilot

The [GCP case guide](../oracles/gcp/README.md) records the accepted startup authoring template and
the complete 24-case pilot: twelve A/B families spanning Cloud Run/migration, observability,
identity/network, managed services and GKE. The [family review records](../oracles/gcp/PILOT.md)
hold supported conclusions, unknowns and official sources outside the candidate workspace. The
catalog continues beyond the pilot in [catalog review records](../oracles/gcp/CATALOG.md), reported
separately from the pilot; the Cloud Run/migration (GCP-03, 04, 06, 07),
observability/identity/network (GCP-10, 11, 14, 16), managed-services (GCP-19 to 24) and GKE
(GCP-26, 27, 28, 30, 31, 32) groups are authored, completing the catalog's offline authoring.

`python scripts/generate_gcp_pilot.py` checks that the generated YAML cases and both review records
match their hidden source data; `--write` regenerates them. `python -m pytest
evals/test_gcp_cases.py evals/test_gcp_pilot.py` exercises paired isolation, real fixture reads,
unavailable observations, tool boundaries and useful/wrong/unavailable controls offline.
Mechanical success remains INCONCLUSIVE pending human semantic assessment. The owner accepted the
64-case catalog on 2026-10-17 (DEC-14); case acceptance does not establish model performance.
