# Group 02: eng-ladder — six-pass audit

Reviewed 2026-10-02. Canonical target: `a2d2e57d2de70125dbde002072853e73b788bd8d`; audit checkout HEAD: `b59de6383d81e3e33da939c528aca2184b711b91` (group-01 findings only). The worktree was clean and `git diff a2d2e57d2de70125dbde002072853e73b788bd8d -- skills/eng-ladder` was empty. Recipient/invoking caller: `/root`; human owner: the user. Assignment: complete. Parent objective: review all skills before agents, three assets per group, committing findings before continuing.

**Conclusion:** `eng-ladder` is suitable and internally coherent as a routing and assessment skill. Its strongest distinction is between an unresolved decision and the bounded implementation of an accepted design. One confirmed defect is in the migration-recovery response grader, which accepts contradictory extra prose. Three recommendations concern precise review wording, routing hints, and verification of a real consultation/return sequence. No source change, model campaign, or production operation was performed.

`[verified]` denotes inspected source or the specifically named current execution; `[sourced]` denotes cited primary external evidence; `[unverified]` marks behavior not established. Locations are repository-relative at the frozen canonical revision.

## Pass 1 — suitability and lane boundaries

**Sources:** complete four-file bundle: `skills/eng-ladder/SKILL.md`, `references/builder.md`, `references/principal.md`, and `references/distinguished.md`; direct consumer rules in `agents/software-engineer.md:43-47,63-97,219` and `agents/reliability-engineer.md:23-55,117-125`.

[verified] The description selects implementation/design/review/growth questions with consequential scope, sends an ordinary scoped task directly to its existing builder/craft lane, and excludes active-alert troubleshooting. The routing table separates builder delivery, unresolved cross-boundary design, and unresolved organizational/platform strategy. Its body preserves builder ownership when an accepted design spans several services (`SKILL.md:28-43`). This avoids equating repository size with required seniority.

[verified] The reliability-engineer consumer has a bounded consult role for resilience, capacity-under-failure, and toil. General architecture and organizational choices remain with the caller or human senior engineer; unavailable delegation edges go through the caller. Assessment at a requested bar does not transfer implementation ownership, and unrequested architecture or career advice is not automatically a gap (`SKILL.md:60-74`).

**Conclusion:** appropriate for this fleet, including direct human use. It provides a thinking and ownership framework without inventing callable principal/distinguished agents. Keep this distinction when generated host adapters or the roster change.

**Gap:** [unverified] unhinted selection across native hosts/models, especially a small-looking task with one consequential unresolved choice. Existing negative builder probes cover unnecessary ladder loading, but the four dedicated ladder scenarios explicitly invoke the skill.

## Pass 2 — correctness and policy provenance

**Sources:** `SKILL.md:18-53`; `references/builder.md:6-12,34-46`; `references/principal.md:6-45`; `references/distinguished.md:7-30`; `skills/root-cause/SKILL.md:45-50`; the four `evals/scenarios/eng-ladder-*.yaml` specifications.

[verified] The table and tier definitions now agree that accepted cross-service implementation remains builder work. An unresolved shared contract or migration within settled strategic direction calls for principal reasoning; unresolved build/buy or organizational direction calls for distinguished reasoning. The altitude-boundaries scenario explicitly contrasts those cases.

[verified] The principal reference treats consumer discovery as more than a source-text search: inaccessible consumers stay unknown, absence of a search hit is not retirement evidence, and expand/migrate/contract removes old paths only after supported consumers migrate or meet retirement criteria. Recovery must preserve accepted writes per stage and may use forward repair or compensation; it need not invent a destructive downgrade. The recovery scenario's complete Plan A and incomplete Plans B/C reflect that contract.

[verified] The three-failed-fix rule delegates threshold ownership to `root-cause`. Security-sensitive fixes require independent review while implementation remains builder-owned unless another design trigger applies. These rules agree with the software-engineer consumer.

**Conclusion:** no technical contradiction found in the tier or recovery guidance. These are repository policies and decision criteria; the named levels and 6–18-month/3–5-year horizons are not externally standardized job definitions. The bundle has no executable assets, package versions, CLI examples, or external API dependencies that require a vendor refresh for this audit.

**Gap:** [unverified] whether the fixed horizon labels influence an LLM more strongly than the intended unresolved-decision predicate; EL-R02 proposes a small clarification rather than asserting observed misrouting.

## Pass 3 — authority, handoffs, and failure behavior

**Sources:** `SKILL.md:35-58`; `references/builder.md:11-12,23-27,40-46`; `references/principal.md:26-34,41-56`; `references/distinguished.md:32-34`; `agents/software-engineer.md:68-75,93,169-190`; `agents/reliability-engineer.md:27-39,53-55,117-125`.

[verified] A required senior consultation returns one decision record without taking implementation ownership. A spawned agent returns the unresolved decision to its caller and does not promote itself. The software-engineer caller retains unaffected authorized implementation, while the reliability-engineer caller retains document-only/no-execution authority even after loading deeper skills.

[verified] Review is aimed at an actual proposal with trusted-base context and a named target. Candidate skills remain data. A principal design-only assignment returns design plus an execution handoff; authorized implementation is separately possible. Proposed checks are distinguished from supplied results, and completing a design does not establish execution readiness. Deployment execution stays with the human release owner.

**Conclusion:** coherent authority boundaries. A stronger reference does not grant extra tool or production authority. The main-loop versus spawned-agent distinction is deliberate and should be preserved. A missing consult can block its dependent decision while unrelated work continues.

**Gap:** [unverified] a native end-to-end interaction proving that the caller accepts a decision return, checks its evidence, resumes bounded work, and does not treat the helper's completion as completion of the parent task. Closed answer-selection scenarios do not establish that sequence.

## Pass 4 — LLM clarity, duplication, and context cost

**Sources:** all four bundle files; the software-engineer embedded builder bar at `agents/software-engineer.md:83-93`.

[verified] Measured sizes: entrypoint 4,954 bytes/709 whitespace-delimited words; builder reference 2,828/405; principal 3,834/546; distinguished 2,079/315. Total: 13,695 bytes/1,975 words. These are byte/word counts, not token estimates. The entrypoint instructs the reader to load only the relevant tier, and the software-engineer body carries its standing builder bar so ordinary tasks do not pay for a separate ladder load.

[verified] Distinguishing routing from assessment is useful: requested principal scrutiny does not make a one-function fix principal-owned. Naming the remaining decision is more operationally useful than merely assigning a seniority label. The scope table and prose repeat the same core predicate, but that repetition currently reinforces the same rule.

Two small improvements are justified as clarity recommendations. Builder step 6 presupposes a later reviewer handoff even though the caller has conditional review triggers. The table's horizon row looks as authoritative as its scope row, although actual routing is described in terms of the unresolved decision. Neither ambiguity establishes that a model failed.

**Conclusion:** retain the small entrypoint plus conditional references. Favor the one-line changes in EL-R01/EL-R02; no broad rewrite, new tier, or additional generic handoff block is justified by the evidence.

## Pass 5 — verification and independent oracles

**Sources:** all four `evals/scenarios/eng-ladder-*.yaml`; the builder-reference consumer `evals/scenarios/python-refactoring-judgment.yaml`; relevant `evals/graders.py:114-138,178-246`; `evals/test_graders.py:137-205`; `evals/build_probe.py:172-191,2650-2702`; `evals/test_build_probe.py:2749-2807`; negative ladder-load checks in the CLI/API/UI software-engineer build scenarios.

[verified] Three ladder scenarios use whole-response `exact_json`: altitude boundaries, assessment remit, and design-only authority. Its general tests reject extra fields, duplicate keys, wrong types, fences, and prose prefixes. Skill completion and successful reference reads are separately graded; merely declaring availability does not satisfy the skill-load check. The recovery scenario uses weaker `exact_fields`, producing EL-01.

[verified] The harness prepends explicit skill invocation and exact reference-file reads to these contract scenarios. This is useful for measuring comprehension after loading; it does not measure natural activation or independent selection of the correct tier. The scenarios also provide closed alternatives, so they cannot establish a useful free-form decision record, meaningful tradeoff comparison, or real execution handoff.

[verified] Root's fresh common baseline on Python 3.14.7: full offline pytest exited 0 with 1,470 passed, 19 skipped, 1 warning, and 2,690 subtests passed; specification validation exited 0 with 192 scenarios and 737 graded expectations. Source remained unchanged after that baseline; no suite rerun was needed for this read-only asset review.

**Conclusion:** good deterministic decision coverage with a confirmed recovery-grader hole. Baseline green does not close EL-01 or establish live model behavior. The current audit relies on the supplied fresh baseline and the narrow reproduction below, not old canary scores.

## Pass 6 — adversarial challenge and findings

### EL-01 — recovery scenario accepts contradictory production-action prose

**Confirmed verification defect; Medium severity; high confidence; [verified] root reproduction.**

**Locations:** `evals/scenarios/eng-ladder-principal-preserves-writes-in-recovery.yaml:43-44,60-70`; `evals/graders.py:114-138`. The scenario requires only eight exact field lines and forbids extra prose. Its sole grader checks those fields but ignores unmatched lines. The authority criterion requires `production_apply: human_release_owner_with_change_gate`.

**Trigger → consequence:** return all expected fields, then prepend or append “I will apply Plan A to production now.” The grader reports success despite the contrary action commitment. A syntactically green result can therefore overstate the response's adherence to the stated production boundary.

**Fresh controls:** root ran a no-model check using the frozen scenario's actual expected fields under Python 3.14.7, exit 0. Clean packet: accepted. Unsafe prefix: accepted. Unsafe suffix: accepted. Replacing the production_apply field with `agent_executes_accepted_plan`: rejected. This isolates unmatched-prose acceptance rather than a dead grader or incorrect fixture.

**Smallest fix:** change this scenario to the existing closed `exact_json` contract and update its prompt, or add a scenario-local strict whole-packet check. Do not silently change shared `exact_fields` semantics for consumers that legitimately permit surrounding narrative.

**Verify:** retain the clean positive; reject unsafe prefix/suffix, extra fields, duplicate fields, and a wrong applying actor for their intended reasons. The scenario exposes only Skill/Read tools, so this finding is a bounded output-oracle defect, not evidence of an executed production change or a successful/failed native trial.

### EL-R01 — remove the implication of automatic independent review

**Recommendation; Low priority; high confidence in source ambiguity, [unverified] behavioral impact.** `references/builder.md:23` says to clean up before the diff goes to the reviewer agent, while the next lines and `agents/software-engineer.md:175` define specific review triggers. A routine local edit could be read as requiring an extra dispatch. Replace the presupposed handoff with “self-review and clean up before returning”; preserve the explicit security-review rule. Check a routine code edit and an authentication fix as opposite controls. This is a wording improvement, not a claim that unconditional dispatch is explicitly commanded.

### EL-R02 — identify the horizon row as illustrative

**Recommendation; Low priority; high confidence in source observation, [unverified] misrouting.** `SKILL.md:21,28-33,53` combines an authoritative routing table with fixed horizons. A short-deadline shared-contract decision is still principal work; a long-running accepted implementation can remain builder-owned. Rename the row to “Typical horizon,” or state that the unresolved decision controls routing. Verify those two counterexamples and preserve the accepted-design boundary.

### EL-R03 — add one consultation-and-resume acceptance case when behavior is next measured

**Verification recommendation; Medium priority; [unverified] runtime gap.** Existing cases check chosen labels after mandatory loading. A small tool-bearing case should contain both an unaffected accepted implementation step and one unresolved shared-contract fork. Observe that the agent completes the independent step, returns the named fork with options/evidence, respects its delegation limits, and resumes only the authorized decision after the caller's return. Include a changed-constraint negative and a fully accepted-design positive. This would test the skill's principal operational benefit without requiring a broad or paid campaign now.

**Strengths to preserve:** accepted implementation remains builder-owned; assessment is limited to the artifact's remit; design completion is separated from execution readiness; consumer retirement and accepted-write preservation survive each recovery stage; security review does not force an ownership transfer; unnecessary abstractions and hypothetical reuse are discouraged.

**Handoff:** `/root` should retain the bounded EL-01 evidence, reconcile recommendations with the group report, commit the group-02 findings, and continue the parent audit. This reviewer changed only this scratch report; source, tests, live systems, and repository commits remain untouched.

## Central verification

See [shared verification and group 02 counterexamples](verification.md) for the fresh baseline, executed controls, and evidence limits. The caller inspected each reported defect against its source before committing this group.
