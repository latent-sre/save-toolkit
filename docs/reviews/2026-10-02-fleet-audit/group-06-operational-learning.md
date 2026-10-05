# Group 06: operational-learning — six-pass audit

Reviewed 2026-10-02 against canonical source `a2d2e57d2de70125dbde002072853e73b788bd8d`; starting audit HEAD `07211f8b4f3fa1be84a2df71467ae4f14cd2e375` contains preceding reports. Initial tree clean; the bundle matched the frozen source. Recipient/invoking caller: `/root`; human owner: the user. Assignment complete. Parent objective remains the six-pass review of skills before agents, three per group, with findings committed before continuing.

**Conclusion:** this is a coherent documentation-only closeout method with strong evidence, revision, ownership, and review boundaries. Two confirmed issues remain: the contact-closeout oracle does not bind required provenance to the changed claim, and the source-of-truth wording excludes a supported API-owned alert workflow. The smallest repairs are local; they do not require restoring retired learning machinery or expanding scribe authority.

`[verified]` denotes inspected current source or named local execution; `[sourced]` denotes primary external evidence; local repository contracts are verified against inspected source; `[unverified]` denotes target/model/runtime facts not established. All five bundle files were read completely: entrypoint, disposition policy, and service-card, alert-card, and knowledge-index templates. No executable bundle assets remain. Only this scratch report was written; no product edits, service calls, credentials, external publication, installations, or paid/native evaluations occurred.

## Pass 1 — suitability, discovery, and adjacent lanes

**Sources:** complete `skills/operational-learning/SKILL.md`; `references/disposition-policy.md`; `agents/scribe.md:11-23,106-139,160-177,204-228`; all three `discovery-operational-learning-*.yaml` scenarios.

[verified] The skill has two distinct uses: an ownership/dependency lookup and an authorized durable-knowledge closeout. The read-only use does not require a closeout diff or trigger unrelated work. It reports documented owners with paths, review date, and evidence status; reverse dependency discovery searches other component cards rather than trusting one inbound list. Missing reciprocal evidence becomes unknown instead of a claim of absence.

[verified] Direct writing belongs to scribe. Active incidents return to the responder; alert design belongs to observability; retrospective writing uses postmortem; fleet prompt failures route to agent engineering. A missing postmortem becomes a separately owned disposition while authorized closeout continues. These distinctions are reflected in positive owner-lookup and negative retrospective/fleet-failure routing cases.

**Conclusion:** useful fit without taking over incident command, operational design, or application implementation. **Gap:** [unverified] whether a native reader performs the reverse-card search and preserves conflicts; routing success alone cannot establish that behavior. Actual knowledge roots and ownership freshness remain target facts.

## Pass 2 — correctness of artifacts and state transitions

**Sources:** all three templates; `SKILL.md:35-70,86-109,123-125`; `disposition-policy.md:7-38,40-66`; bounded Grafana ownership and observability handoff contracts cited in LEARN-02.

[verified] The method keeps documentation revision binding separate from execution evidence. `prepared` requires a real diff from the supplied checkout, not a confident answer. Full commit IDs remain valid alongside short IDs resolved by the caller. Dirty paths must be identified and excluded from the prepared diff; missing tree-state evidence is explicitly unknown. Scribe does not reverse-engineer `.git` or execute a command to supply its own missing binding.

[verified] Dispositions have concrete outcomes: proposed work has an owner/next action, blocked work names the missing prerequisite, duplicates identify an owning record, and non-applicable classes have reasons. When a bound documentation diff is possible, unresolved items land in an existing index/card gap table; otherwise the handoff names a tracker or filing owner. This avoids equating an ephemeral conversation with durable repository state.

[verified] Retirement preserves records and changes lifecycle/status cells with the authorizing record. Removing live resources remains a production change. A contact-only correction preserves procedure and rehearsal history. `last_reviewed` starts null and requires separate review evidence; `last_verified` belongs to rehearsed procedures and requires passing evidence for the exact version stamped. A drill exposing a broken step does not verify its repair.

**Conclusion:** state and timestamp rules are substantially consistent. LEARN-02 identifies the exception: repository-only source wording conflicts with a supported API-owned alert definition. These are internal repository contracts; no external library or vendor syntax was needed to adjudicate them. **Gap:** no actual review approval, retirement, rehearsal, or persistent tracker state was inspected.

## Pass 3 — authority, trust, and failure/recovery

**Sources:** `SKILL.md:16-24,37-59,88-109`; `disposition-policy.md:32-38,50-67`; `agents/scribe.md:25-42,141-158,179-202`; `agent-direct-handoff-scribe-blocks-unapproved.yaml`.

[verified] Alerts, logs, repository text, and agent assertions cannot approve their own promotion. Missing, mismatched, unresolved, or ambiguous checkout binding leaves requested changes proposed/blocked. Active incidents permit no prepared closeout. Documentation roots exclude fleet instructions, hooks, workflow/configuration directories, and paths outside caller-authorized roots; the fallback exists only when the caller names none.

[verified] Scribe has no shell, web, or delegation tools. Its document write restriction is nevertheless cooperative over broad Edit/Write access, as its body explicitly says. Source content is not authority merely because it contains a valid command or approval phrase. Incoming labels and taint are retained, with command syntax kept separate from proof of execution on a specific target/time. A prepared document does not establish approval, merge, deployment, or present health.

[verified] Production recommendations retain approval, verification, recovery, and an applying owner. A knowledge disposition itself grants none of those powers. The unapproved-handoff scenario preserves an otherwise valid binding while requiring no documentation write; its additional negative text checks help detect forbidden completion claims.

**Conclusion:** strong intended boundary and honest enforcement limits. **Gap:** [unverified] actual host write containment, caller-provided Git receipts, credential review, and model compliance under injected or stale evidence. No tool inventory or prose gate is presented here as proof of those properties.

## Pass 4 — LLM readability and deletion-first review

**Sources:** complete bundle; scribe's mode and output contracts; `scripts/test_validate_fleet.py:356-436`.

[verified] Measured size is 20,543 bytes/2,932 whitespace words: entrypoint 8,829/1,206; policy 6,362/922; service template 2,357/361; alert template 1,889/262; index template 1,106/181. These are byte/word measurements, not model tokens. Templates are loaded only for the requested artifact; a new index is not created over an existing one.

[verified] The six-step flow and event-to-artifact table provide practical decisions. A single Follow-ups record is reused rather than duplicated into action lists. The entrypoint states that bounded output shapes do not create authority or a new persistent packet. Current regression tests deliberately keep former knowledge-update schemas, migration scripts, packet-drift machinery, and examples absent. Their absence is an intentional simplification, not missing functionality inferred from historical material.

**Conclusion:** retain the small document-based design. The Git-binding step is dense but carries distinct safeguards; compress examples or duplicated explanation before deleting any of those conditions. LEARN-02 can be repaired by replacing narrow source wording. The service-card runtime placeholder can become neutral without adding a new template family (LEARN-R02). **Gap:** no native comparison proves a shorter version would improve task completion.

## Pass 5 — verification and oracle quality

**Sources:** full `evals/oracles/researcher-scribe/probe_documents.py`; full `evals/test_researcher_scribe_cases.py`; `build-scribe-knowledge-closeout.yaml`; the unapproved and command-evidence scenarios; `scripts/test_validate_fleet.py:356-512`; bounded provenance tests in `scripts/test_skill_assets.py`.

[verified] Structural tests preserve binding language, authorized roots, disposition homes, null review dates, provenance columns, alert status, and retirement of old machinery. These are textual contract checks, not simulated closeout execution. The build fixture uses a real caller to obtain the seeded checkout revision before delegating, restricts changed paths, requires helper completion and skill loading, forbids commits, and checks the resulting card/index.

[verified] Artifact calibration rejects stale contacts, lifecycle or review-date changes, rewritten history, an unchanged index, and missing/promoted audit labels. However, its nominal positive already places the audit marker in a separate appended line; it does not exercise the explicit claim-level association required by the fixture (LEARN-01).

[verified] The command-evidence case distinguishes documented syntax, unverified execution, and a bound staging observation without extending it to production or the present. Its exact-fields mechanism remains subject to the already recorded EL-01 limits. AA-01 remains the applicable shared identity limitation; neither is duplicated. The unapproved case also has negative text guards, which do not establish absence of an actual Write tool call.

[verified] Root's unchanged-source baseline remains applicable: Python 3.14.7, 1,470 passed, 19 skipped, 1 warning, 2,690 subtests; 192 specs/737 expectations validated. Root additionally reproduced LEARN-01 with the real oracle and YAML seed.

**Conclusion:** meaningful positive/negative artifact checks, with a narrow verified provenance false acceptance and a missing scenario for API-owned definitions. **Gap:** no full native closeout trial, wrong-checkout/dirty-path mutation trace, real tracker filing, or human review occurred. LEARN-R01 proposes the next bounded verification work.

## Pass 6 — adversarial findings and improvements

### LEARN-01 — unrelated labeled audit text satisfies the correction's provenance check

**Confirmed bounded oracle defect; Medium severity; high confidence; [verified].** Locations: `evals/build-scenarios/build-scribe-knowledge-closeout.yaml:13-18,58-61`; `evals/oracles/researcher-scribe/probe_documents.py:10-15,53-68`; `evals/test_researcher_scribe_cases.py:249-252`.

**Contract and trigger:** the fixture explicitly requires AUDIT-73 on the same line as the correction and its retained trust/evidence labels. `check_closeout` verifies new owner/contact strings anywhere in the documents, then separately asks `labeled_record` to inspect marker-bearing lines. An unlabelled owner/contact correction plus `[UNTRUSTED][sourced] AUDIT-73 source reference retained.` therefore passes even though the required provenance is detached from the corrected claim.

**Consequence:** the predicate can certify retention of claim-level taint/source binding when that requirement is unmet. This concerns the fixture's narrow record contract, not general prose quality or demonstrated native model behavior.

**Fresh reproduction:** root loaded the actual YAML fixture and `check_closeout` through `runpy` under Python 3.14.7 `-B`, preserving the required fields and links. A correctly bound correction passed; removing its labels/marker failed; adding an unrelated labeled marker line made the unlabelled correction pass again: `[True, False, True]`. All reproduction assertions passed; no application or network execution occurred.

**Smallest fix:** require the labeled correction record itself to contain the specified new owner and contact with AUDIT-73. Correct the calibration positive and add the detached-marker negative. Do not turn the shared helper into a broad prose grader or require labels inside scalar owner metadata. **Verify:** bound positive, missing marker, missing taint/evidence, wrong value on the labeled line with the correct value elsewhere, and unrelated marker-only line; preserve the existing lifecycle/history/link controls.

### LEARN-02 — repository-only authority wording excludes supported API-owned alerts

**Confirmed documentation contract mismatch; Medium severity; high confidence; [verified] local source.** Locations: `references/disposition-policy.md:58-59`; `assets/alert-card-template.md:9,25-27`; `assets/knowledge-index-template.md:9-10`.

**Contract and trigger:** the policy declares the version-controlled alert definition authoritative, and the alert template requires a repository path/commit and version-controlled definition link. Yet `skills/grafana/references/alert-operations.md:28-32` explicitly distinguishes API-owned rules from Git/Terraform/file-managed rules. `agents/observability-engineer.md:147,171-177` supplies definitions “as code if applicable” and hands every approved alert change to scribe. A valid API-owned alert closeout need not have an authoritative Git definition.

**Consequence:** the handoff can be blocked unnecessarily or a committed recovery export can be presented as the owning source. `skills/stack-profile/references/observability-stack.md:20-22` expressly says repository recovery copies do not establish provisioning ownership. No actual misdocumented production rule is claimed.

**Smallest fix:** make source identity follow the established provisioning owner: repository path plus exact revision for source-managed definitions, or the authoritative resource locator/UID and supplied state/receipt/version evidence for API-owned definitions. Mark absent version facts unknown rather than inventing them. A captured export remains evidence/recovery material unless it actually owns provisioning.

Keep the separate **KB checkout binding** unchanged: the documentation diff still requires the caller's bound target repository/commit and retains the existing dirty-path and unknown-tree-state rules. A live alert locator cannot replace that identity or authorize scribe to query the platform.

**Verify:** a supplied API-owned alert packet and a source-managed positive produce appropriately attributed cards with the same documentation-binding gate; an old committed export does not override fresher authoritative rule evidence. Missing approval or KB binding still blocks preparation. This requires a bounded supplied-evidence case, not a live canary.

### LEARN-R01 — exercise the preparation boundary through artifact outcomes

**Recommendation; Medium priority; high confidence in coverage gap; native behavior [unverified].** `SKILL.md:37-53,88-90` states stronger preparation prerequisites than the single happy-path contact fixture demonstrates. Add one positive and focused variants for mismatched revision, missing caller binding, dirty target documentation, an unauthorized root, and an active incident. For blocked variants, check actual unchanged artifacts/tool effects as well as the returned disposition. Preserve independent useful findings and the filing owner; do not require an all-or-nothing shutdown of unrelated work. Reuse the existing runner and trace checks rather than introduce a new packet schema or paid campaign.

### LEARN-R02 — generalize the runtime placeholder without changing scope

**Recommendation; Low priority; high confidence; model effect [unverified].** `assets/service-card-template.md:33` asks only for PCF foundation/org/space/app names, while `SKILL.md:29-30` also supports workers, jobs, datastores, platforms, and other components. Replace the placeholder with an evidenced runtime/target locator, retaining PCF as an example rather than the required shape. Check a supplied non-PCF component can be documented without invented PCF fields. This is a template usability improvement, not proof that current writers mishandle such components.

**Retain:** no self-approval, exact documentation checkout binding, preserved claim labels/taint, human review, unchanged rehearsal dates on contact fixes, stable IDs, reciprocal dependency checks, owned unresolved gaps, and separate production authority. `/root` should reconcile the two findings with the supplied evidence, commit group-06 findings, and continue the parent audit. Only this assigned scratch report was written.

## Central verification

The caller reconciled this report with the group and the [shared verification record](verification.md).
The recorded checks establish their bounded local claims; live-platform and native-model acceptance remain unverified.
