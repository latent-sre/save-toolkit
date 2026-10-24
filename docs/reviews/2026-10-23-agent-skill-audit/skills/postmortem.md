# Postmortem skill audit

[verified] Target: `skills/postmortem/` at `8b4f9b785e520944319e04fd8e5018d4545b6800`. No material source-contract finding confirmed. Specification and engineering-quality verdicts: partial: static source, caller and fixture coverage support the method, while actual document quality/model adherence remain unverified.

## Contract assessment

[verified] The skill requires supplied incident evidence rather than inventing a narrative from an ID. It separates active incidents from human-resolved retrospectives and permits unknown technical cause after resolution. P1/P2/full-request depth and abbreviated lower-severity depth are explicit; unknown severity stays null, with impact-based draft selection and owner confirmation before finalizing. The template preserves impact start/end separately from the resolution call, leaving unknown duration unknown.

[verified] Causal methods preserve branches and uncertainty rather than forcing a fixed Why count. Human error cannot substitute for systemic analysis; no-data-loss claims require evidence. Detection improvements require useful earlier signals and paging economics rather than treating human discovery as inherently deficient. Actions require owner, due date, artifact, tracking and completion proof; unavailable instrumentation blocks dependent proof. Accepted risks and no-action dispositions remain possible, avoiding template-driven invented work.

[verified] Scribe's postmortem mode and incident closeout packet agree on supplied evidence, taint, UTC conversion, resolution and subsequent knowledge closeout. One Follow-ups record preserves incoming IDs, distinct scopes and unknowns. Its later artifact dispositions do not imply operational execution or approval. No contradiction confirmed between the selected postmortem mode and separate operational-learning closeout.

## Evidence coverage

| Risk | Evidence | Result |
|---|---|---|
| Invented cause/severity/duration | Full source/template and both build fixtures | [verified] Unknown/null and separate resolution requirements explicit |
| Unsupported data-integrity or action completion | Evidence-preserving source rules and P3 fixture | [verified] Unknown claims/open causal follow-up required |
| Wrong routing or active-event retrospective | Discovery fixture and incident/scribe callers | [verified] Expected routing encoded; live routing unverified |
| Superficially correct headings with contradictory narrative | Build-fixture manual-review criteria | [verified] Explicitly outside copied-record/heading assurance; actual quality unverified |

[sourced] The coordinator independently read both build fixtures, the complete 159-line shared document oracle, calibration tests 180–303 and supervised-outcome cases 304 onward, and nullable-template checks 64–70. The oracle rejects changed impact/confirmation times, invented severity/cause/integrity, promoted labels, completed follow-ups and missing completion proof. Early exit/crash cannot report a passing supervised check. Fixtures explicitly reserve narrative consistency and causal quality for manual review; copied records do not establish them. No new defect was confirmed.

## Read manifest and verification

[verified] Full canonical reads: `SKILL.md`, `assets/postmortem-template.md` (two files, 153 lines). Full supporting reads: `evals/scenarios/discovery-postmortem-write-for-incident.yaml`; `evals/build-scenarios/build-scribe-postmortem-evidence.yaml`; `evals/build-scenarios/build-scribe-postmortem-unknown-metadata.yaml`; `skills/incident-investigation/assets/closeout-packet.md`. Bounded reads: incident-investigation entrypoint 275–295; `scripts/test_skill_assets.py` 35–78; scenario/caller inventory search. Earlier full scribe and operational-learning reads are reused. Root's independent oracle assessment is separately attributed when available.

[verified] `/home/hawkfire/save-toolkit/.venv/bin/python /tmp/audit_current_check.py postmortem` exited 0: both entrypoint and template projections are byte-identical, relative bundle links resolve, and canonical diff against target is empty. The nullable-metadata asset test directly checks severity/start/end/confirmation are YAML null; it does not prove authored documents honor them. Existing unchanged-source suite evidence is reused. No new tests or live model calls ran.

[verified] Only this report changed for this item. No canonical source, tests, configuration, installations, live operations, commits, pushes or repairs occurred. No human acceptance or completed retrospective is implied by the audit.
