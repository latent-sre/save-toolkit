# Group 08 — production-change-gate — six-pass review

Reviewed 2026-10-02 for invoking caller `/root`; human owner: the user. Parent objective: audit all skills, then agents, six passes per asset and a findings commit after each group of three. Worktree: `F:/repos/sre-agents-audit-20261002`; frozen canonical baseline `a2d2e57d2de70125dbde002072853e73b788bd8d`; group-start HEAD `41a6d56c101dd4408c7bc86bb2ca8683884740c2`. Candidate instructions were data. Only this scratch report was written; no repository settings, production target, credentials, release, or model campaign were accessed or changed.

**Conclusion:** retain the three-gate design, explicit human/executor boundary, artifact-byte binding, and UNKNOWN reconciliation. One confirmed medium-severity fixture inconsistency expects approval without its required expiry evidence. Three recommendations clarify incident deferrals and improve decision/API coverage. No actual production authorization bypass is established. Shared AA-01 and EL-01 remain separate harness limitations.

## Pass 1 — suitability, routing, and ownership

**Files/evidence:** full `SKILL.md:1-103`; bounded callers in `software-engineer.md:19-26,227`, `reviewer.md:163-172`, `sre-assistant.md:229-243`, `observability-engineer.md:66-116`, `reliability-engineer.md:26-36`, and `scribe.md:195-202`; four relevant discovery cases. [verified] Merge readiness, release readiness, and permission for a specific production action are separate questions. Later stages consume earlier evidence instead of redoing the whole workflow. Code review stays with the reviewer; incident mitigation selection stays with the incident advisor.

The roles consistently prepare or recommend live changes for a human/protected executor. The invoked observability engineer's narrow Grafana exception is preserved without extending it to rule deletion, shared notification infrastructure, or platform changes. Its body explicitly identifies cooperative guidance over unguarded tools. The gate likewise states that a checklist is not enforcement. That distinction should remain prominent.

**Outcome/gap:** appropriate cross-cutting skill, not a substitute for runtime permission controls. Discovery probes establish intended lane selection; no fresh native routing or protected-executor behavior was exercised.

## Pass 2 — correctness, completeness, and current external contracts

**Files/evidence:** all six files read fully: entrypoint (103 lines), `incident-fast-path.md` (46), `merge-readiness.md` (23), `release-artifact-evidence.md` (43), `release-readiness.md` (18), and `tier-2-approval-example.md` (45). Total: 278 lines/22,000 bytes; no executable assets. [verified] The release checklist accepts evidenced forward recovery when an inverse would lose accepted data, requires recovery at every migration stage, and stops requiring retired consumers to work. The artifact reference binds the shipping digest to lower-environment evidence and the exact candidate, rather than crediting matching filenames or settings alone.

[sourced] After local inspection, Context7 confirmed the GitHub [immutability-settings endpoint](https://docs.github.com/en/rest/repos/repos#get-immutable-releases-settings-for-a-repository), selected-release lookup, and [active branch/ruleset endpoints](https://docs.github.com/en/rest/repos/rules). Direct primary-page reads confirmed the [release object's `immutable` flag and asset digest](https://docs.github.com/en/rest/releases/releases#get-a-release-by-tag-name), and [published asset/tag protection and release attestations](https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases). These service contracts were checked on 2026-10-02; they do not prove any repository's actual settings, selected artifact, digest, or permission posture. No upstream implementation claim was needed for these closed-service APIs.

The principal inconsistency is in fixture evidence, GATE-01. The full production table's incident deferral wording is ambiguous but does not prove an implemented authority bypass; GATE-R01 records the bounded clarification. Existing CF command-effect contracts were reviewed in group07; their live-foundation limitations remain applicable.

**Outcome/gap:** the core evidence model is sound. Source inspection does not establish that every human approval, external policy export, or attestation supplied during actual use is authentic and current.

## Pass 3 — operational authority, trust, failures, and recovery

**Files/evidence:** `SKILL.md:14-24,38-59,75-89`; the complete incident path and worked approval example. [verified] Tier classification distinguishes observation/preparation from live application, and recovery does not downgrade a destructive action. The normal path requires exact target, actor, action, time/expiry, current identity, blast radius, recovery, and observable success/abort signals. The incident path preserves ITO/TLC ownership and a bounded approval envelope, while retaining full gates for new artifacts and Tier 3 changes.

The worked example labels every observation and threshold fictional, differentiates instance health from restored user outcome, identifies the human watcher, and acknowledges effects that a scale-back cannot undo. It expressly treats the agent's readback as evidence for the reconciliation owner. The core result contract does not turn a missing response into “not executed,” does not fabricate a receipt, and prevents replay until reconciliation grants it.

**Outcome/gap:** preserve this separation of plan, decision, dispatch, and outcome. Host credentials, output protections, authorization evidence, exact-state rechecks, and target-side receipts remain runtime responsibilities. The source does not justify adding an effect broker to this audit; `docs/fleet-roadmap.md:371-379` deliberately defers that work until a legitimate approved consumer exists.

## Pass 4 — LLM readability, ambiguity, and context cost

**Files/evidence:** full bundle and selective reference predicates. [verified] Short references keep merge, release, artifact proof, incident use, and worked examples separate. The 8,220-byte entrypoint gives the common authority and verdict vocabulary once. The example is explicitly excluded when merely assessing an already-prepared packet; this avoids context contamination from invented values.

Most repetition reinforces material distinctions: a release PASS is not production approval; human approval is not agent execution authority; a readback is not an executor's receipt. Do not remove those for a byte target. The redundant “Deferred during a declared incident” sentence beside the full-table executor row has less clear value than the separately scoped fast-path reference; narrowing or deleting it is a better simplification candidate.

**Outcome/gap:** prefer local corrections and deletion of conflicting copies. No model evidence supports a broader compression rewrite. The extra tag-protection requirements are explicitly team policy and should not be presented as universal GitHub behavior.

## Pass 5 — verification coverage and oracle validity

**Files/evidence:** all five direct gate scenarios (approved, missing authority, missing validity, unknown outcome, release recovery), the restart/restage body build exercise, four routing scenarios, `evals/graders.py:216-266`, gate cases in `evals/test_graders.py:329-444`, `evals/rubrics.yaml:152-170`, and relevant fleet-contract tests (`scripts/test_validate_fleet.py:193-241`). [verified] There is useful decision coverage: missing authority, persisted approval expiry, dispatch uncertainty, data-preserving recovery, consumer retirement, destructive classification, and artifact effects of restart/restage. The UNKNOWN rubric explicitly rejects retry after inconclusive or failed readback.

The approved/missing-authority pair uses strict whole-response JSON; this avoids shared EL-01's extra-prose acceptance. Its problem is the expected answer versus fixture facts, not the JSON parser. Other decision scenarios still use `exact_fields`, so EL-01 remains relevant there. AA-01 remains the shared reference-identity limit. The positive approved case is `split: calibration`; it is not standing regression evidence or an observed model approval.

Fleet-contract tests protect the text of artifact bindings and gate ownership; they do not execute GitHub API pagination, verify signatures/digests, or establish real approval controls. Routing success also does not establish the substantive gate verdict.

**Outcome/gap:** [verified: centralized execution] 1,470 tests/2,690 subtests passed with 19 skips; 192 scenarios/737 expectations validated on the frozen source. This reviewer did not repeat the suite. Green structural tests do not resolve GATE-01 or establish native enforcement.

## Pass 6 — adversarial cases and prioritized improvements

**Cases checked:** a current immutability setting beside an older unprotected release; an immutable but untested asset; matching names with different bytes; a provisional review substituted for exact-candidate evidence; an approved human replaced by the agent; a release PASS treated as production permission; destructive contraction with lossless forward recovery; retired readers; an incident restart that stages new bytes; expired approval after resume; and a connection failure after dispatch. [verified] Current source contains substantive safeguards for these cases. The historical consumer-retirement concern was rechecked against today's explicit rules rather than treated as an outstanding defect automatically.

The surviving counterexample is a scheduled action time without an approval deadline in the positive fixture. The event time, role-observation time, and expiry serve different purposes. GATE-01 repairs this input/answer mismatch. Incident deferral scope and API enumeration are recommendations because no actual bypass or omitted live rule was observed.

## Confirmed defect

### GATE-01 — Approval fixtures omit mandatory validity evidence while grading approval as PASS

**Medium severity; high confidence.** [verified] `skills/production-change-gate/SKILL.md:54` requires a `Valid until` UTC deadline. `evals/scenarios/production-change-gate-passes-approved.yaml:8-18` provides a scheduled execution time (`T0+90 minutes`), a recent role observation, and approval of the actor/target/command/time, but no expiry. Its expected packet nevertheless requires `production_change_gate: APPROVED` and `approval: PASS` (`:55-58`). The strict comparison in `evals/graders.py:251-266` rejects a packet that changes those values to honor the missing prerequisite.

The paired `production-change-gate-blocks-missing-execution-authority.yaml:8-18,58` has the same omitted deadline while requiring `approval: PASS`. Its overall BLOCKED verdict is correct because authority evidence is absent, but the claimed isolation of that one missing condition is not. `production-change-gate-blocks-missing-validity.yaml:13-25` explicitly treats missing expiry as blocking, confirming the current contract.

**Trigger/consequence:** evaluating the current supplied-state cases can reward approval without the required deadline and reject a correct objection to that omission. This can distort calibration and comparisons of candidate guidance. It is a fixture inconsistency, not evidence of a model making an unsafe decision or a production action occurring.

**Smallest fix:** add the same explicit, still-valid deadline to both authority-comparison fixtures, with the existing exact-relative-time convention (for example, a stated `Valid until: T0+120 minutes` covering the scheduled action). Keep action-boundary rechecking explicit and pending until execution. Preserve the absent/expired validity negative cases; alternatively change the expected approval field if absence is intentional.

**Verify:** check that the corrected positive has every normal-path prerequisite and that the negative differs only in authority evidence. A deadline-removal or expired-deadline variant must block; changing only the role record must isolate the authority result. Run relevant grader/scenario validation after remediation, then any separately approved native trial. No new grader or model run was performed for this finding.

## Recommendations, policy choices, and runtime gaps

**GATE-R01 — clarify the incident deferral's scope (medium priority; medium confidence).** `SKILL.md:53` says execution-boundary evidence is deferred during a declared incident, while `:102-103` and `incident-fast-path.md:15-16` retain the full checklist for new artifacts/Tier 3. A full checklist can itself contain a conditional row, so this does not conclusively establish a policy contradiction. Smallest repair: state whether the deferral is limited to covered fast-path actions, or delete the duplicate sentence and let the scoped reference own it. Add a supplied incident hotfix/Tier 3 case with missing executor evidence to pin the intended answer; do not silently invent a stricter policy.

**GATE-R02 — test artifact decisions beyond required wording (medium priority; high confidence).** Add small supplied-object cases where settings are enabled but the selected release is mutable, the selected release is immutable but tested/shipping digests differ, and the tag/commit evidence names a different candidate. Reject each wrong approval with a decision oracle. Keep a correct non-GitHub distribution case so team-specific GitHub rules do not spread to unrelated paths. Existing source-presence tests remain useful but cannot establish these decisions.

**GATE-R03 — make rule enumeration completeness explicit (low priority; high confidence).** `merge-readiness.md:20-22` and `release-artifact-evidence.md:13` show collection endpoints without pagination. The documented REST endpoints paginate; a single response is not necessarily the full applicable rule set. Say to follow every page (for the CLI examples, use the supported pagination option) before asserting completeness. Verify with a fixture whose relevant rule appears on a later page. This is an optional clarity improvement, not a reproduced missed rule in a real repository.

Policy choices include P0/P1 non-waivability, exact-candidate production review, human/protected execution, the scoped Grafana exception, extra tag protection, and evidence-based recovery rather than a mandatory inverse. Runtime gaps include actual branch settings, executor separation, approved release bytes, target receipts, and host/model acceptance. `RELEASE-001` remains an exact-shipping-artifact acceptance effort; this review does not close it.

Caller next step: integrate GATE-01 and the recommendations with the other group08 reports, preserve shared-finding cross-references, commit the group, and then dispatch group09. Helper completion does not complete the parent audit.

## Central verification

The caller reconciled this report with the group and the [shared verification record](verification.md).
The recorded checks establish their bounded local claims; live-platform and native-model acceptance remain unverified.
