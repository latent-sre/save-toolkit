# Group 13: scribe — six-pass audit

Reviewed 2026-10-02 against frozen canonical source `a2d2e57d2de70125dbde002072853e73b788bd8d`, in `F:/repos/sre-agents-audit-20261002`. Starting audit HEAD: `a0a4fa12648257a62e8fcf34e0ade355c77b60af`. Invoking caller/return recipient: `/root`; human owner: the user. Assignment complete; the parent objective remains the complete 39-asset audit and final findings commit.

**Conclusion:** no new confirmed Scribe defect was established. The role is useful, its three authoring modes are coherent, and its tools deliberately exclude execution, external retrieval, and model delegation. The main remaining improvements are targeted behavior coverage and modest consolidation of repeated prose. Documentation-only writes and preservation of evidence are still cooperative rules; the source acknowledges that limitation. Existing provenance/oracle and converter findings remain relevant dependencies, not additional Scribe findings.

The complete 239-line agent was read: 16,009 UTF-8 bytes and approximately 2,249 whitespace-delimited words. Review included all three required method entrypoints, their authoring templates, the disposition policy, caller contracts, generated projections, four relevant build fixtures, direct/routing scenarios, both document oracles, and focused calibration/validator/generator tests. No canonical differences from the frozen baseline were present in `agents`, `skills`, `evals`, or `scripts`. Only this reviewer’s scratch report was written; the parent independently updated the shared verification document. `[verified]` denotes inspected source or identified local execution; `[sourced]` denotes fetched primary documentation; `[unverified]` denotes behavior not established.

## Pass 1 — suitability, triggers, and lane boundaries

**Evidence inspected:** complete `agents/scribe.md`; `skills/runbook/SKILL.md`; `skills/postmortem/SKILL.md`; `skills/operational-learning/SKILL.md`; `discovery-scribe-defers-live-incident.yaml`; `discovery-active-alert-stays-with-advisor.yaml`; `discovery-incident-investigation-defers-postmortem.yaml`; `discovery-operational-learning-defers-retrospective.yaml`; and `discovery-runbook-incident-update.yaml`.

[verified] Description and body select an identifiable job: turn supplied operational evidence into a reviewable document. Runbook mode covers an actionable procedure; postmortem mode covers a human-resolved incident; closeout mode updates durable cards, links, and dispositions. Closeout may include a runbook but records a postmortem as a separate owned artifact (`agents/scribe.md:11-23`). This prevents retrospectively applying a procedure template to causal analysis or silently widening a contact correction into a complete documentation rewrite.

[verified] An unknown cause does not reopen a resolved incident (`83-98,171-173`). Active incidents return to the human responder; alert design goes to observability, undecided automation to reliability, and accepted implementation to software engineering. These are recommendations to the caller, not dispatches from Scribe. The routing scenarios cover active-versus-resolved distinctions, while required methods are selected before writing (`204-211`).

**Remaining gap:** routing definitions are intended behavior, not observed routing reliability. Mixed requests still require the caller to sequence primary artifacts. No current native model run established how reliably it makes that choice.

## Pass 2 — correctness, tools, projections, and dependencies

**Evidence inspected:** `agents/scribe.md:1-42,141-186,204-211`; `scripts/validate_fleet.py:118-155`; `scripts/test_validate_fleet.py:319-328,527-545`; `scripts/generate_platform_adapters.py:160-173,280-287,312-323,360-419`; `scripts/test_platform_adapters.py:205-220,275-306`; both generated Scribe files; delegation-graph source; current official Claude documentation through Context7.

[verified] The explicit Claude grant is exactly `Read, Grep, Glob, Edit, Write, Skill`. The validator requires that set and rejects execution, external-evidence, and delegation additions. A mutation test adds Bash, WebSearch, and Agent and expects both authority and graph failures. Scribe has no direct MCP dependency. Its method-loading dependency is explicit, with a stop when the required skill cannot load.

[sourced] Current official documentation says a subagent tool list limits available tools and omitting `Agent` prevents spawning subagents: [subagent tool restrictions](https://code.claude.com/docs/en/agent-sdk/subagents) and [Claude subagents](https://code.claude.com/docs/en/sub-agents), fetched through Context7 on 2026-10-02. This corroborates the declared capability design; it does not prove an installed host honored these particular files. No upstream implementation claim required GitHits investigation.

[verified] Both Copilot projections have `tools: ["read", "search", "edit"]`, no model-delegation grant, and the same SHA-256, `625752a37c75acd0735da8d08890bf34b0980ba15f6995bd19652d0ae5069d5e`. The human-selected “Automate approved procedure” handoff preserves approval, target binding, taint, and recovery requirements. The generator explicitly distinguishes that transition from an agent dispatch. Existing adapter tests pin both distinctions; shared baseline validation covers generation freshness. Repository definitions are not evidence of current Codex registration.

**Remaining gap:** native permission resolution, installed skills, UI handoffs, and actual filesystem containment were not exercised. Generated-byte parity proves matching files, not runtime authority enforcement.

## Pass 3 — authority, provenance, paths, and recovery

**Evidence inspected:** `agents/scribe.md:29-42,112-158,179-232`; operational-learning entrypoint `37-70,86-125` and complete disposition policy; all three knowledge templates; complete runbook and postmortem templates; `agents/software-engineer.md:176`; `agents/observability-engineer.md:171-191`; `skills/service-lifecycle/SKILL.md:80-86`; and complete `skills/incident-investigation/assets/closeout-packet.md`.

[verified] Scribe cannot establish a checkout identity by running Git. A Bash-holding caller supplies observed revision and status evidence. `prepared` requires an actual authorized diff and a verified binding to the mounted target; absent, ambiguous, or mismatched binding leaves an owned proposal/block. The method separately excludes pre-existing dirty paths, rejects traversal and unauthorized roots, and forbids deriving the binding from `.git/` contents. A matching HEAD does not itself prove a clean tree. These are valuable explicit preconditions, not an assertion that Read/Edit performs Git verification.

[verified] Writing does not approve, merge, deploy, or rehearse the artifact. New runbooks start draft with null review/rehearsal dates; postmortem times permit nulls and distinguish impact end from later resolution confirmation. Existing contact corrections preserve operational history. Human review and exact-version rehearsal govern separate metadata. The caller contracts carry revision, approval, receipts, labels, and non-actions rather than letting the helper manufacture them.

[verified] Command syntax provenance and target execution are different claims. A supplied `[verified]` observation can be retained only with exact command bytes, target, actor, and result; relevant time and source identity remain attached. Sourced syntax does not establish current production health. Untrusted input remains data, conflicting claims remain uncertain, and production recommendations preserve the change gate. Runbook publication does not authorize the reader to execute its actions.

**Remaining gap:** Edit/Write are not restricted to documentation by this frontmatter. A malicious instruction inside an incident transcript could still influence a model with a broad file-write tool; no present bypass was demonstrated. The source states this cooperative boundary and points to requested scope, human diff review, and outer filesystem permissions (`29-31`). LEARN-02 owns the separate mismatch between repository-only alert provenance and supported API-owned alerts. RUN-01/RUN-02 own importer races and command corruption; Scribe is instructed to have a human/software engineer run that converter, not execute it itself.

## Pass 4 — readability, ambiguity, and context cost

**Evidence inspected:** entire agent; method entrypoint loading and template selection; `agents/scribe.md:55-79,81-104,106-158,179-239`.

[verified] Mode headings, a short pressure/response table, exact return fields, and explicit non-actions make the role usable for both an invoking agent and a human. Small edits preserve structure; first/thin runbooks load the example; knowledge closeout loads only needed templates. The 2,249-word body does not force all references into every task. However, provenance, taint, and non-action requirements recur across the boundary, doctrine, rules, output, and mode sections.

**SCR-R03 — Low priority, high confidence; optional readability improvement.** Locations: `agents/scribe.md:27,69-70,143-158,181-186,193-199,226-232`. A reader encountering “every command … must come from evidence” and later “an unsourced command remains unverified” must distinguish a supplied but unsupported snippet from an invented command. The direct command-evidence fixture makes that intended distinction, so this is not a proven contradictory authority grant. Consolidate the common evidence rule and say “a supplied but unsourced command” once; use short references from modes. Remove repeated generic non-action wording while retaining its final return requirement, exact execution binding, claim-specific taint, time/target scope, and the independently useful pressure examples. Verify preserved rule coverage and compare context size after any future edit; do not remove unique safeguards merely to hit a word target.

**Remaining gap:** shorter prose is a hypothesis for better comprehension. No token-efficiency or behavior improvement was measured; do not label proposed compression a verified optimization.

## Pass 5 — verification quality and actual coverage

**Evidence inspected:** all four build fixtures (`build-scribe-writes-only-docs`, `build-scribe-postmortem-evidence`, `build-scribe-knowledge-closeout`, `build-software-engineer-resumes-after-scribe`); both direct Scribe scenarios; complete `probe_runbook_slots.py` and `probe_documents.py`; `evals/test_researcher_scribe_cases.py`; `scripts/test_runbook_schema.py`; `evals/test_build_probe.py:110-121`; validator binding tests `438-491`; and `evals/README.md:286-291,322-339`.

[verified] Coverage is substantive: document-only paths, no Bash/commits, typed draft frontmatter, null dates, filled sections, routed expected outcomes, rollback association, sourced placeholders, escalation, taint preservation, no invented verified execution, distinct syntax/execution claims, preserved contacts/history, and a completed helper plus resolving README link. Calibration mutates labels, owners, dates, lifecycle, and provenance; schema tests bind template/exemplar shape and copied approval boundaries.

[verified] Limits are also disclosed. The return/resume fixture does not prove who edited README or when; the closeout fixture requires manual trace inspection for caller authorship and checkout binding. The artifact oracle calls itself bounded rather than a general document-quality judge. Green regex/field checks do not prove operational safety, staffed escalation, correct causal reasoning, or fulfilled follow-ups.

Shared findings remain applicable: LEARN-01 covers marker-to-claim provenance binding; POST-R01 covers status/action/proof coverage beyond the ownership check; POST-R03 covers a full-form unknown-metadata fixture; EL-01 covers exact-fields acceptance of unrelated prose; AA-01 covers the identity limits of reference-read evidence. Do not duplicate those mechanisms or count their repairs as new Scribe work.

**SCR-R02 — Low priority, high confidence; method-loading coverage improvement.** `agents/scribe.md:206-211` requires `runbook` before procedure writing, but `build-scribe-writes-only-docs.yaml:60-103` lacks a `skill_loaded` check. Postmortem and closeout fixtures already include theirs (`:25` and `:55`, respectively). An artifact matching the template does not establish that the current method was loaded. Add the same bounded check, with wrong/missing method negative calibration and the shared AA-01 identity limitation explicitly retained. This is missing coverage, not proof the agent skipped its skill.

The parent’s frozen baseline remains **1,470 passed, 19 skipped, 2,690 subtests**, with **192 specifications/737 expectations** validated. No full-suite rerun or new executable counterexample was needed for this report. Offline passes do not establish native model acceptance.

## Pass 6 — counterexamples, simplification, and ranked next steps

**Evidence inspected:** source preconditions above; `agent-direct-handoff-scribe-blocks-unapproved.yaml:3-49`; positive closeout build `4-18,53-61`; binding/path phrase tests; complete document calibration. The following are proposed adversarial cases, not observed incidents or new confirmed defects.

**SCR-R01 — Medium priority, high confidence; closeout behavior coverage improvement.** Current exact-field refusal supplies a valid binding, absent approval, and the desired decision literals; the positive build supplies an approved contact edit. Neither establishes writing behavior with an approved request but a missing/mismatched binding, a forbidden destination, or conflicting current evidence. Trigger: one of those prerequisites is wrong while the rest appears valid. Consequence if mishandled: a helper could claim `prepared` or edit the wrong artifact; this remains `[unverified]`, not a demonstrated write bypass.

The smallest useful extension is a bounded disposable closeout fixture with paired valid/invalid inputs. First vary binding only; then test an unauthorized root and a same-path pre-existing edit. Require no artifact mutation when blocked, preserved dirty bytes, one owned follow-up, and no newly asserted approval/verification. Keep the existing positive contact case to guard against refusing valid work. Add a conflicting-source case that preserves both references and uncertainty. Calibrate each oracle with explicit wrong outputs before any separately authorized native run. Attribution and trace inspection remain necessary; final-file equality alone cannot prove the absence of attempted writes. This extends disclosed coverage, not a claim that the present oracle falsely advertises it.

**Priority and preserved strengths:** prioritize the existing LEARN/RUN findings for owner disposition under AUDIT-001, followed by SCR-R01’s focused negative coverage and SCR-R02’s small method assertion. Consider SCR-R03 only with preserved-contract verification. Keep terminal tools absent, retain separate writing/approval authority, keep null metadata and exact-version rehearsal, reuse one Follow-ups record, and return the helper result to its invoking caller. Do not add a new approval service, persistent packet schema, or duplicated KB ledger to solve these bounded issues.

**Caller next step:** adjudicate the three recommendations and existing cross-references, integrate this final agent report into group 13 and the cross-fleet rollup, then commit the findings. The review prepared no operational document, ran no procedure or model campaign, changed no canonical source, and made no approval or release decision.

## Central verification

The caller reconciled this report with the group and the [shared verification record](verification.md).
The recorded checks establish their bounded local claims; live-platform and native-model acceptance remain unverified.
