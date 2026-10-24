# Production change gate skill audit

[verified] Target: `skills/production-change-gate/` at `8b4f9b785e520944319e04fd8e5018d4545b6800`. Source specification: partial; engineering quality: partial. No material source-contract defect confirmed. One P3 evaluation-contract finding is documented below; the positive calibration conflicts with the required approval-expiry evidence.

## P3 — AUDIT-GATE-001: positive approval calibration omits the required validity deadline

[verified] High confidence. `skills/production-change-gate/SKILL.md` line 54 requires an authorized approval with a `Valid until` UTC deadline. `evals/scenarios/production-change-gate-passes-approved.yaml` supplies the approver, actor, target, planned action/time and change record (17–23), but no validity deadline anywhere. Its exact JSON oracle nevertheless requires `production_change_gate: APPROVED` and `approval: PASS` (56–59). The paired missing-execution-authority fixture likewise expects approval PASS (59) and every non-authority item passing while supplying no deadline.

[verified] Trigger: evaluate either supplied packet under the current full production checklist. Consequence: a response that correctly flags missing expiry cannot satisfy the positive fixture's exact expected answer; the paired fixture cannot isolate execution authority as its sole missing item. This weakens calibration and can penalize correct gate adherence. Counterevidence: the separately reviewed `production-change-gate-blocks-missing-validity` fixture explicitly expects BLOCKED for absent expiry, and source rules remain clear. These fixtures do not grant actual production access; no live unsafe approval was observed. Minimal repair direction: add explicit current expiry evidence to both fixtures intended to have passing approval, retaining the missing-validity case as the negative control. Record the executor's pre-action recheck obligation separately from a completed future check. No repair was made.

[verified] Coordinator reproduction used the actual `evals/graders.py:exact_json` function with each fixture's declared fields. The expected packet passed for both cases; a packet retaining the other fields while setting `approval: FAIL` and `production_change_gate: BLOCKED` failed both. This confirms scoring behavior, not a model execution. Full root reads included both fixtures and the missing-validity negative control, with bounded calibration lines 290–375. Severity is P3 because measurement correctness is the direct demonstrated impact; the fixtures grant no live production capability.

[sourced] Official GitHub [release](https://docs.github.com/en/rest/releases/releases#get-a-release-by-tag-name), [repository immutability](https://docs.github.com/en/rest/repos/repos#check-if-immutable-releases-are-enabled-for-a-repository), and [rules](https://docs.github.com/en/rest/repos/rules) references support the selected-release `immutable`, current-policy `enabled`, and active tag update/deletion checks. These are separate properties: current policy does not prove past immutability. Tag ruleset conditions and bypass visibility require care; a branch active-rules endpoint is not a tag endpoint. No actual repository control was queried. Root also read the complete release-artifact reference and the restart/restage six-proposal build case; no new source contradiction was found there.

## Source contract and coverage

[verified] Merge, release and production decisions consume earlier records without recursively rerunning them. Exact candidate/CI/review identity, immutable tested bytes, migration compatibility and per-stage recovery are separated from production authority. Recovery need not be a lossless inverse, but must preserve accepted writes; retired consumers do not remain required forever. Tier 3 effects retain classification even with tested recovery.

[verified] The production checklist distinguishes a named executor from actual role/credential-boundary evidence, requires approval expiry and action-time rebinding, and forbids agent execution outside the invoked observability Grafana exception. That exception matches the observed agent body: scoped complete procedures, prior state, readback and UNKNOWN reconciliation, with excluded actions still human/protected-executor owned. Approval does not prove an effect; missing receipts remain UNKNOWN and require named reconciliation before retry.

[verified] The incident path covers only declared, reversible existing-artifact actions with bounded ITO approval, recovery and serving headroom. New artifacts, unknown staging state, whole-app stop/start, Tier 3 and suspected compromise stay outside it. Deferred administrative records never defer effect reconciliation. Tier 0 reads remain bounded by lane and output protection.

| Risk | Evidence | Result |
|---|---|---|
| Wrong merge/release/production boundary | Six canonical files and discovery fixtures | [verified] Distinct required evidence and verdicts |
| Missing authority, expiry or result | Five production decision fixtures | [verified] Explicit decision cases; positive expiry mismatch above |
| Recovery confused with inverse or lower tier | Release-preserves-recovery fixture | [verified] Per-stage accepted-write preservation, separate production authorization |
| Incident restart creates new artifact | Restart/restage build fixture | [verified] Six effect-based decisions; no live execution |
| Host protection and model adherence | No connected executor or live eval | [unverified] Static guidance does not enforce production boundary |

## Read manifest and checks

[verified] Full canonical reads: `SKILL.md`; `references/incident-fast-path.md`, `merge-readiness.md`, `release-readiness.md`, `release-artifact-evidence.md`, `tier-2-approval-example.md` (six files, 275 lines). Full supporting reads: all five `evals/scenarios/production-change-gate-*.yaml`; all three `evals/scenarios/discovery-production-change*.yaml`; `evals/build-scenarios/build-production-change-gate-classifies-restart-and-restage.yaml`. Bounded reads: observability-engineer 40–90, reviewer 162–175; software-engineer/CI caller and grader-test inventory searches; exact finding locations. Earlier PCF-ops/deploy reads are reused. Root's oracle/public-source pass is separately attributed.

[verified] `/home/hawkfire/save-toolkit/.venv/bin/python /tmp/audit_current_check.py production-change-gate` exited 0: all five reference projections and the entrypoint are byte-identical, local links resolve, source diff against target is empty. Existing unchanged-source suite results are reused. The coordinator ran only the bounded grader reproduction above; no live model or production command ran. Passing structural tests cannot reconcile a wrong fixture expectation with its specification.

[verified] Only this report changed for this item. No source/test/configuration repair, installation, live operation, commit, push or acceptance occurred. Human review remains required for disposition of the finding and eventual exact candidate acceptance.
