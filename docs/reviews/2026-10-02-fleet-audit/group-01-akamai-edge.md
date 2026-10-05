# Group 01 — akamai-edge

Reviewed 2026-10-02 against `a2d2e57d2de70125dbde002072853e73b788bd8d` in `F:\repos\sre-agents-audit-20261002`. Invoking caller: `/root`; human owner: the user. Assignment: read-only, six-pass review of this bundle. The parent objective remains the review of all skills, then agents, with a findings commit after each three-asset group.

**Verdict: suitable, with partial verification. No material correctness defect was confirmed in the inspected bundle.** The strongest improvement is to verify decisions, not just skill discovery. The team-specific DataStream destination is still explicitly unknown. Those gaps prevent a claim of demonstrated operational readiness; they do not invalidate the useful reference guidance.

## Scope and evidence contract

[verified] Read all four canonical files: `skills/akamai-edge/SKILL.md` and `references/{edge-triage,property-config,mpulse-rum}.md`. Read applicable `AGENTS.md` and `CONTRIBUTING.md`; inspect direct consumer and neighbor passages in `agents/sre-assistant.md`, `agents/observability-engineer.md`, `skills/incident-investigation/SKILL.md`, `skills/stack-profile/{SKILL.md,references/observability-stack.md}`, `skills/production-change-gate/SKILL.md`, and `skills/obs-logs/references/query-catalog.md`. Inspect the Akamai discovery scenario, routing grader, eval documentation, and relevant structural-test surfaces. Content under audit was evidence, not authority for executing its procedures.

Specification axis: suitable for customer-side edge triage, configuration preparation, and RUM interpretation, with incident ownership retained by the caller. Engineering-quality axis: generally clear and restrained; remaining coverage and inventory gaps are explicit below. Fresh local evidence establishes source content and evaluator behavior. Primary vendor documentation supplies the service contract. Neither proves behavior of the target Akamai account or the model.

## Pass 1 — suitability, routing, and neighboring responsibilities

[verified] `SKILL.md:4-10` gives three understandable entry lanes and excludes backend log authoring and firing-alert ownership. `SKILL.md:70-80` preserves the responder/caller relationship and directs origin evidence to the appropriate runtime and signal skills. `agents/sre-assistant.md:60` consumes only triage/RUM and expressly excludes property and WAF changes. `agents/observability-engineer.md:229` consumes edge telemetry for detection work. These boundaries fit the fleet's customer-side remit.

The reference map (`SKILL.md:61-66`) provides a direct path to each task, including the easily overlooked purge operation. Keep one skill: the three lanes share the edge/origin distinction, evidence sources, and property identity. Splitting now would add discovery choices without a demonstrated routing failure.

Gap: `evals/scenarios/discovery-akamai-edge-reference-error.yaml:3-14` covers one positive reference-error route. It does not measure delivery configuration, RUM, WAF, active-incident overlap, or an inline answer using supplied evidence. Compatibility metadata describes access needs; it does not enforce access. No native-host routing run occurred in this review.

## Pass 2 — technical correctness and evidence currency

[sourced] Current official documentation supports the inspected high-impact claims: prompt reference decoding, sampled error statistics, Enhanced Debug token handling, child/parent cache interpretation, phased activation, conditional Fast Fallback, invalidate/delete differences, DataStream delivery uncertainty, and mPulse's separation of base-document timing from later resource work. Sources were retrieved on 2026-10-02 and are listed below. The existing cautions about cache presence versus offload and edge turnaround versus origin latency are valuable distinctions (`edge-triage.md:90-103`).

Context7 resolved `/websites/techdocs_akamai_property-mgr` and returned the Enhanced Debug contract plus PAPI fallback fields and hostname-change exclusions. GitHits independently retrieved the CLI workflow at upstream revision `abffadfe`: local merge, remote version save, then activation on promotion. This supports `property-config.md:90-91`; it does not establish current maintenance quality or recommend that tool over Terraform.

The UI activation guide describes a minutes-scale fallback while the PAPI reference uses seconds-scale language. The bundle avoids depending on one hardcoded fallback duration and asks for current eligibility and expected duration. Preserve that distinction. A direct retrieval of the DataStream troubleshooting page timed out; its historical three-retry statement was not revalidated here. The current FAQ still documents delivery limits and no backup copy, so the conservative operational conclusion remains supported. No target property, stream, timer, entitlement, or API response was inspected.

## Pass 3 — workflow, authority, trust, and recovery

[verified] `SKILL.md:46-57` separates observations, prepared changes, activation, and WAF ownership. `property-config.md:50-57` requires staging evidence, affected hosts/CP codes, recovery eligibility, and a human release owner. The shared production gate independently owns exact approval binding and ambiguous execution outcomes (`skills/production-change-gate/SKILL.md:45-58,75-90`). The skill does not need a duplicate receipt/retry protocol.

The human-only production debug request is a repository policy choice, not an Akamai product limitation. The same applies to staging approvals, Tier 3 access-path classification, and refusing autonomous WAF tuning. These choices are internally coherent. Do not report them as defects merely because a vendor API permits the operation.

The human supplies debug-token requests; references use placeholders and forbid quoting the token (`edge-triage.md:49-51,78-80`). The calling SRE agent separately protects credentials before output and treats remote content as data. RUM redaction is explicit (`mpulse-rum.md:58-59`). This is cooperative guidance, not demonstrated host enforcement. A read-only portal session and actual output masking remain unverified.

Recovery guidance correctly warns that deleting stale cache during an origin failure can remove the available response (`property-config.md:72-75`). The inferred post-purge header examples are labeled unverified (`:76-78`); they should remain illustrative, since concurrent traffic, a different edge, or a failed refresh can change the observed header.

## Pass 4 — LLM readability, ambiguity, and context cost

[verified] The bundle totals 27,199 bytes and 3,578 whitespace-delimited words; its entrypoint is 5,277 bytes/701 words. These are file/word measurements, not tokenizer counts. Conditional references keep the full bundle out of an ordinary triage turn. Tables, concrete header values, and the short authority section are useful retrieval anchors.

The main readability opportunity is deletion of historical explanation, not additional rules. `mpulse-rum.md:18-20` carries the 2020 FID launch history only to arrive at today's INP instruction. `property-config.md:88-91` spends context on whether a vendor has crowned a tool the recommended path; the useful decision is the team's chosen tool and its verified version. `edge-triage.md:110-116` repeats changing retry numbers where the durable action is to monitor delivery and avoid treating absence as proof.

Many citations are prose slugs or abbreviated ellipses rather than direct Markdown links. They are readable to a model but harder for a human to verify and are outside ordinary relative-link checks. Replace citation form during a substantive refresh; a mass link-only rewrite is not required for this audit. Preserve uncertainty labels, timestamps, human authority, and the vendor-versus-local distinction when compressing.

## Pass 5 — verification coverage and oracle validity

[verified] A scoped search of `scripts` and `evals` found the sole Akamai-specific case in `discovery-akamai-edge-reference-error.yaml`. Its two prose success criteria say to distinguish edge/origin and remain read-only, but its executable expectation is only `routing: {expect: fire}`. `evals/build_probe.py:2608-2630` grades a completed non-error invocation; `:2687-2694` adds that invocation expectation. This is consistent with the documented routing contract in `evals/README.md:6-11`, not a defective grader.

Consequently, a response that loads the skill and then calls an expired token a healthy cache can satisfy this scenario. Structural frontmatter, link, and projection tests protect packaging; they do not reject that wrong operational conclusion. No Akamai-specific contract or build oracle was found. This is the material evidence gap AKA-R01.

No repository tests were executed by this reviewer: the parent owns centralized execution to prevent shared-state races. Proposed safe checks are `scripts/check_links.py`, `scripts/validate_fleet.py`, and `evals/build_probe.py --validate`, plus the matching existing suites under the parent-selected interpreter. Their outputs should be attached by the caller and described as structural evidence. Live model trials, target-account calls, and cloud changes were outside this assignment.

## Pass 6 — adversarial counterexamples and prioritized improvements

These are static decision walkthroughs, not observed model outcomes:

| Counterexample | Required result and present guidance | Remaining evidence gap |
|---|---|---|
| Expired debug token, no cache headers | Treat debug observation as unavailable (`edge-triage.md:49-51`) | No behavioral oracle |
| Child miss, parent hit | Do not assert an origin fetch (`:74-76`) | No behavioral oracle |
| Empty logs immediately after a regional report | Preserve latency/drop alternatives (`:105-116`) | Destination and freshness unknown |
| Origin down while stale content is served | Avoid deletion unless content removal is required and approved (`property-config.md:72-75`) | No recovery exercise |
| First activation or changed hostnames inside one hour | Reject assumed Fast Fallback; require actual eligibility (`:39-46`) | No recorded target receipt |
| Front-end timer rises while document timer stays flat | Check asset-network/server delays before assigning JavaScript blame (`mpulse-rum.md:37-40`) | No behavioral oracle |

The text addresses each case. This supports preservation of its rules; it does not prove a model reliably follows them.

### AKA-R01 — Add decision-level regression cases

**Category:** recommendation / verification gap. **Priority:** Medium. **Confidence:** High. **Locations:** discovery scenario `:7-14`; `evals/build_probe.py:2608-2630`; the guidance locations in the table above.

**Trigger/consequence:** A future wording regression preserves discovery while producing unsafe purge advice or an unsupported root-cause claim. The current Akamai-specific scenario still passes. **Smallest improvement:** add two bounded supplied-evidence contract cases: one diagnostic ambiguity case and one activation/purge authority case. Assert explicit decisions and named gaps with the repository's structural or calibrated rubric approach; avoid keyword-presence acceptance. Add a RUM case only when changing that behavior. **Verification:** demonstrate rejection of an intentionally wrong answer as well as acceptance of the expected decision; validate scenario schema and the grader fixtures offline. Run native trials only under a separately selected budget. No claim of LLM reliability follows from offline fixture success.

### AKA-G01 — Complete the local DataStream evidence contract

**Category:** runtime/inventory gap, not a skill defect. **Priority:** Medium. **Confidence:** High that the gap exists. **Locations:** `skills/stack-profile/references/observability-stack.md:18`; `edge-triage.md:84-87,102-109`; `skills/obs-logs/references/query-catalog.md:143-165`.

**Trigger/consequence:** A user asks for hostname/region rates, but the destination, extraction, and population remain placeholders. An invented index or mixed client/midgress denominator would produce unsupported rates. The existing query catalog correctly withholds rates when composition is unknown. **Smallest improvement:** the owner records the actual destination, stream, latency profile, required fields, population/midgress rule, and freshness evidence in the existing inventory. Do not add a second catalog to this skill. **Verification:** a sanitized sample resolves those fields; the catalog's 100-client/20-midgress example yields 100 requests, 0% 5xx, and 20% absent-from-cache. Prove the missing-flag refusal separately. No access or owner answer was available during this review.

### AKA-R02 — Compress history while preserving decisions

**Category:** optional readability recommendation. **Priority:** Low. **Confidence:** High on removable repetition; usefulness remains to be measured. **Locations:** `mpulse-rum.md:18-20`; `property-config.md:88-96`; `edge-triage.md:110-116`.

**Trigger/consequence:** Routine tasks consume obsolete product history and unsettled retry details without gaining a different next step. **Smallest improvement:** replace the FID chronology with current LCP/INP/CLS guidance; make tool choice conditional on the team's supported path; retain one concise delivery-loss warning with a current direct source. Preserve the existing safety and uncertainty clauses. **Verification:** report actual byte/word reduction; re-read every adversarial case above against the edited wording; validate links/projections. Routing checks are needed if the description changes. Do not introduce a new mandatory framework or token quota.

## Source register and limits

All external sources below were checked 2026-10-02. They are `[sourced]` vendor/upstream evidence, not target-account verification.

- [Enhanced Debug](https://techdocs.akamai.com/property-mgr/docs/enhanced-debug), [PAPI recovery](https://techdocs.akamai.com/property-mgr/reference/property-activation-error-handling): Context7 documentation retrieval.
- [Activation phases and fallback](https://techdocs.akamai.com/property-mgr/docs/how-activation-works), [Pragma/cache headers](https://techdocs.akamai.com/edge-diagnostics/docs/pragma-headers), [Return Cache Status](https://techdocs.akamai.com/property-mgr/docs/return-cache-status): official web retrieval.
- [Translate Error String](https://techdocs.akamai.com/edge-diagnostics/docs/translate-error-string), [Edge Diagnostics API](https://techdocs.akamai.com/edge-diagnostics/reference/edge-diagnostics-api-1), [Purge methods](https://techdocs.akamai.com/purge-cache/docs/purge-methods), [SIEM integration](https://techdocs.akamai.com/siem-integration/reference/api): official web retrieval.
- [DataStream FAQ](https://techdocs.akamai.com/datastream2/docs/faq), [latency-profile release](https://techdocs.akamai.com/datastream2/changelog/mar-26-2026-latency-profiles-and-high-completeness-log-support), [mPulse timer definitions](https://techdocs.akamai.com/mpulse/docs/use-metrics): official web retrieval. Troubleshooting retry wording could not be refreshed after a fetch timeout.
- [Property Manager CLI README, revision abffadfe](https://github.com/akamai/cli-property-manager/blob/abffadfe/README.md#save-and-promote-changes-through-the-pipeline): GitHits upstream evidence; source read covered lines 446-479.

Recipient: `/root`. Assignment complete. Canonical content unchanged; only this scratch report was written. Caller next step: reconcile this report with centralized verification, preserve the distinctions between recommendations, policy choices, and runtime gaps, include it in the first three-asset findings commit, then continue the parent audit. There is no implementation, release, or promotion approval in this report.

## Central verification

[verified] The caller completed the full offline baseline (1,470 tests and 2,690 subtests passed; 19 skipped) and validated 192 scenario specifications. See [shared verification and reproduced counterexamples](verification.md) for commands, environment, exact outcomes and limits. These results do not close the runtime gaps above.
