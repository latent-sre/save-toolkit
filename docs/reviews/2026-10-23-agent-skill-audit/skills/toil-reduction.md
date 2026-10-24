# Toil reduction skill audit

[verified] Target: `skills/toil-reduction/` at `8b4f9b785e520944319e04fd8e5018d4545b6800`. No material source-contract finding confirmed. Specification and engineering-quality verdicts: partial. The method and callers are consistent; real savings, safety benefits and model adherence require independently supplied measurements.

## Contract assessment

[verified] Evidence mode assesses supplied records without interviewing. Thin direct human requests permit one relevant batched interview, while dispatched agents return gaps/questions to the caller. Questions cannot manufacture requirements or block the assessment indefinitely: unknowns become labeled gaps after answers or reinvocation. Direct selection of an agent retains the human interview mode. Existing gist-level answers are not redundantly requested.

[verified] Baselines count distinct interventions rather than ticket/page/runbook duplicates and cover a natural task cycle or disclose partial coverage. Total effort includes interruptions, rework, approvals and transferred maintenance across teams. Options include cause correction, simplification, self-service and explicit acceptance rather than assuming automation. Recurring restarts are diagnostic leads, not evidence that automated restart is the correct remedy.

[verified] The equations preserve units and comparable windows. Nonpositive savings have no positive time-saving break-even; independent risk benefit must be justified separately. Uncertain costs use ranges, proposer optimism needs observed comparators or disclosed accepted margins, and slow adoption/useful-life limits require cumulative horizon comparison. Fictional examples correctly calculate 6 baseline hours, 2 net hours and 20-month payback; 30–50 build hours and 1–3 net hours give outer bounds of 10–50 months without asserting independence.

[verified] Recommended automation must specify target binding, idempotency/partial/UNKNOWN behavior, bounds, observability, recovery and manual fallback. Implementation and live authority remain with their existing owners. Before/after comparison includes total work and outcomes under comparable demand; faster code/fewer tickets alone cannot prove benefit. Reliability-engineer and runbook callers invoke this assessment before automation decisions rather than granting execution or durable-record authority.

| Risk | Evidence | Result |
|---|---|---|
| Invented baseline or duplicate effort | Entrypoint and worked examples | [verified] Distinct interventions, natural cycle and gaps required |
| Hidden maintenance/negative ROI | Equations and positive/negative examples | [verified] All-team costs, nonpositive case and horizon uncertainty explicit |
| Unnecessary interviewing | Entry-mode contract | [verified] One relevant round for thin direct requests; no dispatched interview |
| Automation masks service defect | Recurring restart example and caller | [verified] Cause/risk analysis precedes automation |
| Actual benefit/model execution | No new operational measurement/live eval | [unverified] Method does not establish realized savings |

## Read manifest and checks

[verified] Full canonical reads: `SKILL.md`, `references/worked-examples.md` (two files, 219 lines). Bounded supporting coverage: reliability-engineer/runbook/software-engineer caller search; toil discovery/build scenario inventory. Earlier full reliability-engineer and runbook reads are reused. Root owns independent evaluation/oracle and primary-source support.

[verified] `/home/hawkfire/save-toolkit/.venv/bin/python /tmp/audit_current_check.py toil-reduction` exited 0: entrypoint/reference projections match byte for byte, local Markdown links resolve and canonical diff against target is empty. Existing unchanged-source baseline is reused; no new tests, live measurement or model call ran in this pass.

[verified] Only this report changed for this item. No canonical/test/configuration edit, installation, live action, commit, push, repair or acceptance occurred.

[verified] Root fully read the positive, negative and duplicate-record toil scenarios; exact expected arithmetic is 6/2/20, 6/-1/no-positive-payback, and 20 distinct interventions/5 baseline/3 net/10 months respectively. The already-reviewed proportionate-options build case separates measured baseline from estimated benefit and rejects expanded authority. These are supplied-record decision checks, not realized savings or interview-quality evidence. [sourced] Google's [Eliminating Toil](https://sre.google/sre-book/eliminating-toil/) supports the method's distinction between repetitive operational work and engineering/overhead; Google's own allocation target is not imposed as team policy. No new material defect was confirmed.
