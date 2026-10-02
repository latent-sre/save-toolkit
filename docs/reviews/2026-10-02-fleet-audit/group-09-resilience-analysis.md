# Group 09: resilience-analysis — six-pass audit

Reviewed 2026-10-02 against frozen canonical source `a2d2e57d2de70125dbde002072853e73b788bd8d`; audit HEAD at dispatch was `8cbf3664f87a314e0373be287a515a4f542e15b1`. Recipient/invoking caller: `/root`; human owner: the user. Assignment complete. The parent objective remains the six-pass review of skills before agents, three per group, with findings committed before the next group.

**Conclusion:** no new confirmed defect was established in this scope. The method is technically careful and suitable for evidence-led failure analysis: it traces effects to user outcomes, seeks effective controls, distinguishes conditional risk from observed failure, and makes experiments falsifiable without granting authority to perform them. The useful improvements are verification of required method loading and a focused capacity-under-failure example/case. Neither warrants adding a general resilience checklist, a score, or a new framework.

`[verified]` identifies inspected frozen-source facts or the explicitly identified existing offline baseline; `[sourced]` identifies retrieved primary publications; `[unverified]` identifies target/runtime/model claims not established. All four bundle files were read completely: `SKILL.md`, `references/failure-scenarios.md`, `references/worked-contrasts.md`, and `references/sources.md`. Bounded consumers, relevant fixtures, grader implementation and tests, generator behavior, and generated copies were inspected. Only this assigned scratch report was written. No source repairs, installs, live operations, new test execution, paid/native model campaign, or commits occurred.

## Pass 1 — suitability, triggers, and lane boundaries

**Evidence:** complete entrypoint; `agents/reliability-engineer.md:3-55,57-76,107-125`; complete `discovery-resilience-analysis.yaml` and the bounded reliability discovery cases for assessment, active incident, lifecycle, root cause, change review, and accepted implementation under `evals/scenarios/`.

[verified] The description identifies concrete slow-dependency, failure-propagation, degraded-behavior, and recovery-design tasks. It distinguishes active incidents, inventory/readiness checklists, and independent change verdicts. The body starts with a critical user transaction or batch/data outcome, accepted requirements, and environment, rather than applying a pattern catalog before identifying the problem.

[verified] The principal consumer gives this skill failure propagation, capacity, recovery, and reliability design; toil economics, observed-cause diagnosis, data mechanics, and consequential shared decisions retain their specialized methods. Its source/design-document lane excludes execution and implementation. The overlapping routing cases explicitly distinguish an active incident, a missing lifecycle record, diagnosis of a reproduced failure, PR review, and accepted code work.

**Result:** coherent scope with useful neighbor boundaries. The skill can help a human or an agent without becoming a new production owner. **Gap:** native discovery and useful investigation remain unverified in this audit; these YAML cases describe expected routing, not proof that a host will register or dispatch the role.

## Pass 2 — technical correctness and primary-source support

**Evidence:** complete `failure-scenarios.md` and `worked-contrasts.md`; `SKILL.md:21-45,49-80`; all of `sources.md`; four cited Google SRE chapters retrieved on 2026-10-02.

[verified] The scenario table covers slow dependencies, overload, loss of a failure domain, partial completion, mixed versions, restoration, control-plane/vendor loss, misleading telemetry, and operator procedures. It asks for effective callers/configuration and shared constraints. Configured connection maxima are potential demand, not observed allocation; differently named replicas do not prove independence. Batch freshness/completeness and request latency/useful response quality are distinguished.

[verified] The retry arithmetic is accurate and carefully limited: three total 12-second attempt budgets sum to 36 seconds, but backoff and other work can extend elapsed time; three retries may mean four attempts. A 20-second overall deadline does not make a third attempt impossible when earlier failures are fast. Caller return also does not establish downstream cancellation or resource release. The complete worked proposal retains unknown commit/deduplication semantics, compares isolation/deadline propagation with replicas, and measures unrelated work as well as the affected operation.

[sourced] The cited methods match their stated uses. Google's [cascading-failure chapter](https://sre.google/sre-book/addressing-cascading-failures/) discusses retry amplification, overload, deadline propagation, and cancellation; [Non-Abstract Large System Design](https://sre.google/workbook/non-abstract-design/) grounds design in explicit assumptions, physical capacity, and failure behavior. The skill does not copy their example thresholds into service defaults.

[sourced] [Testing for Reliability](https://sre.google/sre-book/testing-reliability/) distinguishes version/configuration consistency and bounded test evidence; [Implementing SLOs](https://sre.google/workbook/implementing-slos/) ties objectives to users and stakeholder agreement. This supports the skill's separation of accepted requirements from proposed targets. These publications are guidance, as `sources.md:3-6` says, not company policy or proof of skill performance.

**Result:** no material technical contradiction found. No version-specific SDK/API mechanism or upstream code implementation required Context7/GitHits research; direct primary book chapters supplied the relevant methodological evidence. **Gap:** the historical claim that two pinned public skill examples informed organization was not independently reconstructed; their authority/defaults are explicitly excluded by `sources.md:15-19` and none is load-bearing here.

## Pass 3 — workflow, authority, trust, and failure recovery

**Evidence:** `SKILL.md:14-17,25-28,39-45,60-63,71-85`; `failure-scenarios.md:27-30`; `worked-contrasts.md:57-77`; `agents/reliability-engineer.md:23-39,59-86,109-125`; bounded `skills/stack-profile/SKILL.md:93-109` ownership rules.

[verified] The method grants no access, execution, design approval, or change authority. Experiments stay proposed until an authorized actor supplies results from an established environment. Staging is expressly not presumed harmless. A failed query or inaccessible source creates a gap, and absence of observation does not rule out an alternative. Missing accepted thresholds stay unknown or become explicit proposals.

[verified] The consumer limits edits to requested assessment/design documents, sends operational observations through the existing SRE access path, sanitizes public research questions, and forbids privilege expansion. Its write restriction is acknowledged as cooperative unless enforced by the host. Helpers return evidence; the caller retains implementation and independent review assignments. Platform ownership and pending target decisions remain governed by stack-profile.

[verified] Recovery checks cover user outcomes, data integrity, backlog drain, and reconciliation rather than restart/alert/backup success alone. The worked test specifies observations that would falsify the proposal, stop bounds, removal of injected delay, and recovery before calling the test complete. Same-version evidence can close a particular lead while leaving other paths and larger loads untested.

**Result:** strong authority and uncertainty boundaries with practical recovery criteria. **Gap:** no host containment, real helper exchange, fault-injection environment, target authorization, or actual service recovery was validated. Those limitations do not prevent a scoped design assessment from completing.

## Pass 4 — LLM readability and context cost

**Evidence:** full bundle; consumer method/output contracts at `agents/reliability-engineer.md:41-55,78-105`; generator skill-copy path at `scripts/generate_platform_adapters.py:525-550`; direct hashes of all four `.github/skills/resilience-analysis/` projections.

[verified] Measured bundle size is 16,379 bytes, 213 lines, and 2,153 whitespace-separated words: entrypoint 5,886/87/768; scenarios 3,240/30/445; contrasts 5,554/77/782; sources 1,699/19/158. These are not token measurements. All four generated copies are byte-identical to canonical files. Inspected canonical method, consumer, grader, and fixture files have no diff from the frozen source.

[verified] The four result classes are compact and useful: observed defect, supported design risk, verification gap, and improvement opportunity. Keeping result type separate from evidence label prevents a sourced conditional risk from being relabeled as a measured incident. The explicit permission to find nothing counteracts finding quotas and missing-pattern criticism.

[verified] Progressive loading is proportionate: select relevant scenario rows; consult worked contrasts for distinctions and the source note for provenance. Examples explain why a tempting conclusion fails, then show what evidence would settle it. The main slow-ledger example is longer but includes distinct owner, alternatives, falsification, stop, and recovery details.

**Result:** preserve the compact entrypoint and claim boundaries. Do not add mandatory per-scenario output slots or a general health score. If a new capacity contrast is justified, replace/extend the short replica example instead of appending another large worked assessment. **Gap:** no measured model comparison shows that further shortening or adding text improves outcomes.

## Pass 5 — actual verification and oracle limits

**Evidence:** complete `evals/test_reliability_cases.py`; complete reliability redelivery, document-boundary, and partial-helper build cases; deadline-controls, recovery-evidence, supplied-helper-return, and native-helper scenarios; `evals/README.md:502-518`; `evals/graders.py:178-266`; relevant exact-JSON calibration at `evals/test_graders.py:178-283`; bounded adapter delegation tests.

[verified] The deadline supplied-state case recognizes an effective overall deadline plus cancellation and preserves sourced/tainted evidence without certifying the service. The recovery case separates a current backup from an older restore lacking business validation and accepted objectives. The helper cases reject an old r7 override as proof of r8 safety and require continued assessment. The native conversation additionally asks the reader to update a scoped conclusion after stronger r8 evidence arrives; its success criteria retain redelivery and larger-load gaps.

[verified] The redelivery fixture establishes a sequential, in-memory persistence contract with an unguarded and guarded path. Its offline test executes those reviewed fixture functions: after acknowledgement failure and redelivery, the expected balances are 20 versus 10. Concurrent atomicity and retention are expressly outside scope. Pair-identity tests keep the reliability and SRE incumbent comparison equivalent. Document-boundary tests reject configuration changes even alongside an allowed assessment file.

[verified] The strict JSON grader rejects whole-response prose/fences, duplicate/missing/extra keys, type-coercible values, nonfinite values, and unsafe nesting. Calibration mutates each expected decision field. EL-01's extra-prose weakness concerns a different grader and is not duplicated here.

[verified] Free-form document checks are intentionally limited: the document-boundary case checks path, a dependency token, and non-actions; prose quality and source reads require manual trace review. The partial-helper regex is a narrow textual sentinel, not a general stance verifier. README explicitly preserves these limits and leaves native acceptance open. Required skill loads are not asserted in the build cases (RES-R01).

The root's frozen-source baseline remains applicable: 1,470 passed, 19 skipped, 2,690 subtests; 192 specifications/737 expectations. No suite or focused executable case was repeated. **Gap:** offline calibration does not prove source investigation, reference loading, effective native delegation, model competence, or operational benefit.

## Pass 6 — counterexamples and ranked improvements

### RES-R01 — verify required method loading in an appropriate build case

**Recommendation; Medium priority; high confidence in coverage gap; model behavior unverified.** Locations: `SKILL.md:14-15`; `agents/reliability-engineer.md:23,43-45`; `evals/build-scenarios/build-reliability-engineer-doc-boundary.yaml:36-42`; `build-reliability-engineer-redelivery.yaml:59-78`; `evals/test_reliability_cases.py:48-57`.

**Trigger and consequence:** a build run can produce the expected result or permitted document without loading stack-profile or resilience-analysis, and current automatic checks do not distinguish it. Source retrieval is already disclosed as manually reviewed; method adherence likewise remains an unverified aspect rather than something established by a green build verdict.

**Smallest improvement:** add `skill_loaded` assertions for stack-profile and resilience-analysis to the candidate-only document-boundary case, or record explicit completed-load checks in its manual trace rubric. If requiring load before effects, state that ordering in the fixture and use the supported before-effects check. Do not mechanically alter the identical redelivery comparison pair, and do not add unavailable Skill calls to intentionally Read-only supplied-state cases.

**Verification:** a synthetic trace with the document but no required loads fails the added check; matching successful loads pass; attempted/failed loads do not satisfy it. Preserve existing path/non-execution controls and exact pair identity. Template/reference use and quality still need independent evidence. This is a coverage extension, not a new confirmed false-advertising defect.

### RES-R02 — cover capacity after failure and recovery from overload with one bounded contrast

**Recommendation; Low priority; high confidence in representativeness gap; model behavior unverified.** Locations: `SKILL.md:6,42,76-78`; `failure-scenarios.md:9-10,18-25`; `worked-contrasts.md:31-44`; `evals/test_reliability_cases.py:12-43`.

**Trigger and consequence:** the skill promises capacity-under-failure analysis, but detailed calibration concentrates on deadlines, redelivery, restore evidence, and helper provenance. A writer could handle those well while equating replicas with surviving useful capacity or treating stopped queue growth as completed recovery. That behavior was not observed; the present coverage does not resolve it.

**Smallest improvement:** expand the existing short replica contrast with explicitly supplied normal demand, surviving effective capacity, shared bottlenecks, and backlog-drain evidence. Pair a supported capacity shortfall with a contained counterexample; keep assumptions and units visible and avoid guessed failure probabilities or generic headroom targets. Reuse the existing supplied-state test style for classification, with manual review of the reasoning when a native run is separately authorized.

**Verification:** distinguish configured maxima from measured throughput, normal from remaining capacity, and stabilized backlog from drained accepted work. An alternative with adequate surviving capacity and bounded recovery should permit no material finding in that scope. Unknown allocation or independence should remain a gap. Prefer replacing a weak example over growing a new checklist.

**Disposition:** no new confirmed RES defect; two recommendations and explicit runtime gaps. Preserve the smallest-change comparison, existing-control counterexamples, all four result classes, conditional arithmetic, falsifiable experiments, and separate human authority. `/root` should adjudicate this report, commit group 09 findings, and continue the parent audit; this completed assignment does not close the overall review.

## Central verification

The caller reconciled this report with the group and the [shared verification record](verification.md).
The recorded checks establish their bounded local claims; live-platform and native-model acceptance remain unverified.
