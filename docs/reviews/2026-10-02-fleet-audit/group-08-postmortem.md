# Group 08: postmortem — six-pass audit

Reviewed 2026-10-02 against frozen canonical source `a2d2e57d2de70125dbde002072853e73b788bd8d`; audit HEAD at dispatch was `41a6d56c101dd4408c7bc86bb2ca8683884740c2`. Recipient and invoking caller: `/root`; human owner: the user. Assignment complete. The parent objective remains the six-pass skills-then-agents audit, three assets per group, with a findings commit before the next group.

**Conclusion:** no new confirmed postmortem defect was established. The two-file skill is concise, suitable for evidence-bound retrospective writing, and consistent with its principal consumer. Preserve its uncertainty, human-resolution, and action-ownership rules. The useful improvements are a narrower template wording correction and proportionate verification of follow-up meaning and the unexercised full/unknown-metadata branches. The already recorded LEARN-01 provenance mechanism also applies to this oracle and is cross-referenced rather than counted again.

`[verified]` identifies inspected frozen-source facts or explicitly named offline execution; `[sourced]` would identify fetched primary external evidence; `[unverified]` identifies behavior or target facts not established. Both bundle files were read completely: `skills/postmortem/SKILL.md` and `assets/postmortem-template.md`. There are no bundled executable helpers, dependencies, or additional references. No uncertain public API contract required external research. Only this assigned scratch report was written; no source edits, installations, live operations, commits, or paid/native model evaluations occurred.

## Pass 1 — suitability, triggers, and lane boundaries

**Evidence:** complete entrypoint; `agents/scribe.md:3-23,81-104,160-177,204-232`; complete `discovery-postmortem-write-for-incident.yaml`, `discovery-incident-investigation-defers-postmortem.yaml`, `discovery-operational-learning-defers-retrospective.yaml`, and `discovery-scribe-defers-live-incident.yaml` under `evals/scenarios/`.

[verified] The skill selects one resolved incident retrospective. Its description gives concrete requests, sends writing to scribe, and sends active incidents to incident-investigation. The body also supports a main-thread reader without pretending that the skill itself grants tools. Summary/explanation requests explicitly remain summaries. Given only an incident ID, the writer asks for timeline, closeout evidence, and severity instead of producing an apparently complete empty artifact.

[verified] The adjacent methods have distinct jobs: incident-investigation establishes recovery and supplies a closeout packet; postmortem explains the incident; operational-learning records durable knowledge dispositions. Scribe is explicit that unknown cause does not reopen an incident whose human resolution is recorded. Its lack of delegation means the skill's named follow-up lanes are recommendations returned to the caller.

**Result:** appropriate scope and useful positive/negative discovery coverage. **Gap:** [unverified] actual host registration, unhinted routing, and successful multi-step handoff; scenario definitions alone prove none of these. P1/P2 versus P3/P4 depth selection is repository policy, not a universal severity standard.

## Pass 2 — correctness of facts, metadata, and artifact structure

**Evidence:** entire template; `SKILL.md:18-30,34-57,71-73`; complete `skills/incident-investigation/assets/closeout-packet.md`; bounded incident recovery contract at `skills/incident-investigation/SKILL.md:287-290`; `scripts/test_skill_assets.py:134-156`.

[verified] Known times are quoted RFC3339 UTC, while unknown endpoints remain YAML null and estimates belong in the timeline. Duration uses impact start/end, never the later resolution confirmation. The incoming closeout contract likewise converts only dated, zoned source times and preserves unresolved clock facts. A resolved incident therefore need not acquire a fabricated exact end time.

[verified] Severity remains null when unknown. Evidenced customer-visible or multi-service impact selects a full draft in that case; otherwise the abbreviated form is used, with the choice explained and confirmed before finalization. Both forms retain Summary, Timeline, Assessment, and Follow-ups. Full analysis adds impact magnitude/denominator, causal method, alternatives, detection/response, luck, and lessons. The author removes selection instructions and unused sections rather than shipping both forms.

[verified] The method distinguishes trigger, mechanism, defenses, and remaining uncertainty; does not force a linear Five Whys story; and requires evidence for a no-data-loss assertion. Actions need artifact, completion proof, owner, due date, and tracking link. Missing instrumentation becomes a prerequisite only where needed. Human detection is evaluated by delay, available signals, and paging cost rather than automatically declared a defect.

**Result:** no factual contradiction requiring repair. The lucky-item wording is unnecessarily narrower than the action policy (POST-R02). **Gap:** no real incident impact, causal result, data-integrity check, or action completion was independently established.

## Pass 3 — workflow, authority, trust, and recovery

**Evidence:** `SKILL.md:25-27,48-62,66-73`; `assets/postmortem-template.md:74-84`; `agents/scribe.md:25-42,141-158,179-202,226-232`; `skills/operational-learning/SKILL.md:37-70,86-90`; `scripts/generate_platform_adapters.py:200-213` and `scripts/test_platform_adapters.py:316-339`.

[verified] The author retains incoming evidence labels without promotion. Scribe additionally treats repository, incident, tool, and handoff material as untrusted data, prefixes derived findings with taint, and requires human review. Its tools omit execution, external lookup, and delegation; its broad Edit/Write grants still make documentation-only path discipline cooperative. The skill does not independently expand those grants.

[verified] One Follow-ups record preserves incoming IDs and separates distinct scopes, owners, and evidence. Knowledge closeout enriches it rather than replacing it with a second list. A `prepared` disposition requires a bound checkout and actual diff and proves neither approval nor execution. The generated incident-closeout handoff also rechecks resolution, authorization, and checkout binding, while preserving a knowledge-only request's primary artifact.

[verified] Missing causal certainty is handled by an owned next check; missing required facts stay unverified; genuinely inapplicable fields carry a reason. Production safety work routes to the human release owner. These are useful recovery paths from incomplete evidence without inventing certainty or performing remediation.

**Result:** no new authority conflict. **Gap:** host containment, a real caller's checkout receipt, malicious incident-text resistance, and human review are unverified. Nothing in this review establishes a document as approved for operational use.

## Pass 4 — LLM readability, ambiguity, and context cost

**Evidence:** complete two-file bundle; scribe's mode/output contracts; generator's skill-copy path at `scripts/generate_platform_adapters.py:525-550`; direct hash comparison of both `.github/skills/postmortem/` copies.

[verified] The entrypoint is 4,337 bytes, 73 lines, and 597 whitespace-separated words; the template is 3,405 bytes, 84 lines, and 473 words. Combined cost is 7,742 bytes/1,070 words, not a token measurement. Both generated copies are byte-identical to their canonical files in this checkout. Relevant canonical source and oracle files have no diff from the frozen baseline.

[verified] The skill provides a small decision path: establish context, select depth, preserve evidence, analyze proportionately, and retain owned follow-ups. The full-only subtree is visibly isolated. The template's table combines tracking, scope, ownership, status, prerequisites, proof, and evidence; references elsewhere avoid duplicated action lists. The main ambiguity is the narrower lucky-item placeholder described below.

**Result:** retain this small bundle; no new schema, reference tree, or general writing framework is justified. A deletion-first change can remove the extra category restriction in one placeholder. Do not remove null/uncertainty rules merely because scribe repeats them: direct main-thread use makes those lines useful. **Gap:** no measured model comparison establishes that further compression improves completion or reduces omissions.

## Pass 5 — verification quality and limits

**Evidence:** complete `evals/build-scenarios/build-scribe-postmortem-evidence.yaml`; complete `evals/oracles/researcher-scribe/probe_documents.py`; relevant calibration source `evals/test_researcher_scribe_cases.py:189-239`; `scripts/test_skill_assets.py:134-156`; `scripts/test_validate_fleet.py:514-532`; `evals/README.md:332-339`; bounded harness checks at `evals/build_probe.py:1924-1930,2229-2239,2459-2462`.

[verified] The P3 build fixture supplies separate impact/recovery and human-confirmation times, unknown cause/data integrity, and an existing follow-up. It limits changes to one requested file, requires skill loading, forbids shell attempts and commits, and runs a separate artifact probe. The shell prohibition checks attempted PowerShell as well as Bash calls. Structural asset tests preserve nullable severity/times and the revision placeholder. Lane tests reject execution/egress/delegation grants in scribe.

[verified] The artifact oracle checks draft status, exact quoted timestamps, nullable review date, four required headings, omission of full analysis, one FUP-72 row retaining Casey and the due date, and labels on named source/gap records. Calibration includes wrong recovery time, final status, missing owner/heading, newly verified claims, and individual lost/promoted evidence or taint labels. These are meaningful negative controls.

The oracle header and README explicitly disclose bounded field checks rather than general document quality. Consequently, missing causal-prose grading, action semantics, or full-form coverage are recommendations/gaps, not proof of a broken advertised general grader. Its marker-only provenance association is the same mechanism as [LEARN-01](group-06-operational-learning.md); no duplicate POST finding is created. Skill loading also does not prove the template was read or correctly applied.

[verified] The root's frozen-source baseline remains applicable: 1,470 passed, 19 skipped, 2,690 subtests; 192 scenario specifications/737 expectations. No suite was repeated here. **Gap:** no native postmortem generation, live routing, production evidence validation, or approval workflow was exercised.

## Pass 6 — counterexamples and ranked improvements

### POST-R01 — extend follow-up verification only where its meaning matters

**Recommendation; Medium priority; high confidence in the coverage limit.** Locations: `evals/build-scenarios/build-scribe-postmortem-evidence.yaml:14-16`; `evals/oracles/researcher-scribe/probe_documents.py:44-46`; `evals/test_researcher_scribe_cases.py:203-207`.

**Trigger and consequence:** a writer can preserve FUP-72, Casey, and the date while dropping the causal investigation and completion proof or changing its status. The current predicate checks only those three retained identifiers/values. Its accepted calibration row has no question or proof column. Passing this check therefore establishes ownership retention, not preservation of the work needed to resolve the unknown cause.

**Smallest improvement:** make the fictional positive include the supplied causal question, open status, and reviewed-finding-or-explicit-limit completion criterion; add targeted field assertions only if that stronger guarantee is wanted. Preserve the existing bounded-check disclaimer rather than presenting semantic document quality as deterministic proof. **Verification:** retain the valid row; reject a completed-without-evidence status, omitted question, and unrelated proof criterion while keeping owner/date controls. This is an extension of disclosed coverage, not a new confirmed oracle defect.

[verified] Root exercised the actual `check_postmortem` with the AST-extracted calibration artifact in an owned temporary directory: original open row passed; changing only open to completed also passed; changing Casey to unknown failed. All reproduction assertions passed. No model or external service was involved; the result establishes this narrow coverage boundary only.

### POST-R02 — align the lucky-item placeholder with the general action policy

**Recommendation; Low priority; high confidence in wording difference; model impact unverified.** Locations: `assets/postmortem-template.md:63-65`; `SKILL.md:46-47,64-67`.

**Trigger and consequence:** a narrowly avoided long outage may justify a mitigative recovery improvement. The skill permits justified mitigative or preventative actions without a category quota, while the full template asks each lucky item to become a preventative action or accepted risk. A literal reader may misclassify a useful recovery action or add unnecessary recurrence-prevention work.

**Smallest improvement:** replace the placeholder's preventative-only restriction with the skill's existing “justified follow-up or explicit accepted risk” wording. This removes a redundant constraint without adding prose or changing the blameless policy. **Verification:** read a full-form near-miss example with a mitigative-only action and confirm it remains valid; preserve the requirement to address an evidenced risk. No native failure is claimed.

### POST-R03 — add one focused unknown-metadata/full-form acceptance case when this area changes

**Recommendation; Low priority; high confidence in scenario gap; runtime behavior unverified.** Locations: `SKILL.md:18-27`; `assets/postmortem-template.md:5,8-10,23-25`; current build fixture `:5,9-13`.

The only artifact fixture supplies P3 and exact impact endpoints. It does not exercise a customer-visible resolved incident with unknown severity or missing impact-end time. Such a writer should choose the explained full draft, retain null fields, keep duration unknown, and preserve the human resolution confirmation without reopening live investigation. Reuse the existing fixture/checker with bounded metadata/heading assertions and manual causal review when authorized; do not add a new reporting schema or infer model success from static template tests. Retain summary-only and active-incident routing boundaries.

**Disposition:** no new confirmed POST defect; three recommendations and the shared LEARN-01 cross-reference. Preserve the compact bundle, nullable facts, separate clocks, evidence labels, human-resolution gate, systemic analysis, and one owned Follow-ups record. `/root` should adjudicate this report, commit group 08 findings, and continue the remaining audit; this assignment alone does not complete the parent objective.

## Central verification

The caller reconciled this report with the group and the [shared verification record](verification.md).
The recorded checks establish their bounded local claims; live-platform and native-model acceptance remain unverified.
