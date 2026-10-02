# Group 05 — obs-logs — six-pass review

Reviewed 2026-10-02 for invoking caller `/root`; human owner: the user. Parent objective: review all skills, then agents, three assets per committed group, six passes per asset. Source: `F:/repos/sre-agents-audit-20261002`, canonical baseline `a2d2e57d2de70125dbde002072853e73b788bd8d`; group-start HEAD `e68e5e4f17a782b4eedc3aa0df30cc550bf40227`. Candidate instructions were review data. Only this scratch report was written; no source, query execution, platform change, dependency installation, or model campaign.

**Conclusion:** retain this skill and its present ownership boundaries. Two confirmed documentation defects can misdirect an investigation: Cloud Logging payload-key case handling, and Splunk freshness conclusions outside the queried event-time range. Two focused recommendations concern performance interpretation and decision-level coverage. Target inventory and backend execution remain explicit runtime gaps. There is no basis for a general readiness verdict.

## Pass 1 — suitability, routing, and neighboring ownership

**Files/evidence:** complete `SKILL.md:1-90`; direct consumers `agents/sre-assistant.md:46-67`, `agents/observability-engineer.md:218-229`; six routing scenarios named below. [verified] The description distinguishes log interpretation/query construction from metrics, dashboard design, Grafana operations, alert design, and live incident advice. The body scales work to the question: explaining supplied output does not require inventing a new query or baseline (`SKILL.md:16-17`). Correlation results return to the caller; saved searches, alerts, and panels are recommendations to the owning lane (`:65-77`).

The positive correlation-id and Cloud Logging scenarios, negative live-page and alert-design scenarios, and the Grafana/trace neighboring negatives cover useful boundaries. The phrase “why are there 500s” overlaps live incidents, but the same description explicitly routes deciding a live page to `incident-investigation`, and a negative scenario exercises that distinction. This is an intentional boundary requiring behavioral evidence, not a demonstrated routing defect.

**Outcome/gap:** suitable reusable query method for human responders and bounded helpers. No new agent or skill is justified. Routing definitions establish intended choices; no fresh native routing trial ran.

## Pass 2 — technical correctness and currency

**Files/evidence:** every line of `references/spl.md` (249), `logql.md` (210), `gcp-logging.md` (146), `indexes.md` (59), and `query-catalog.md` (181), plus the 90-line entrypoint. Six files total 935 lines/53,404 bytes; no scripts or executable assets are bundled. [verified] Good technical controls include request-completion denominators, independent per-phase totals, invalid/missing-status coverage, complete buckets, exclusion of the current bucket from the baseline, the flat-baseline branch, and preserving unknowns when ingestion is unproven. Loki distinguishes errors/sec from request quality and requires matching offsets on both numerator and denominator (`logql.md:142-172`). Cloud Logging separates filtering from aggregation (`gcp-logging.md:22-26`).

[sourced] Current primary documentation was retrieved through Context7 after local inspection: Google Logging field identifiers and Splunk 10.4 event/index time modifiers substantiate LOG-01/02 below. Splunk job-property documentation leaves a transformation-related ambiguity relevant to LOG-R01. [Grafana's log-query documentation](https://grafana.com/docs/loki/latest/query/log_queries/#pattern) supports the published pattern-parser guidance; no unsupported syntax defect is asserted. [Google's quota and retention page](https://docs.cloud.google.com/logging/quotas), checked 2026-10-02, confirms the 60/minute `entries.list` limit and 400-day `_Required` retention. One small precision opportunity: `gcp-logging.md:143-146` should qualify configurable `_Default` retention as applying to **project** buckets; folder/organization defaults are fixed. The surrounding query guidance already binds projects, so this is a scope clarification rather than another ranked defect.

**Outcome/gap:** two confirmed corrections, not wholesale rewriting. External documentation proves documented contracts, not the team's target parser, ingestion completeness, installed versions, performance, or permission behavior. `tstats max(_indextime)` is already explicitly unverified with a fallback (`spl.md:60-62`); that acknowledged limitation is not a new finding.

## Pass 3 — operational workflow, trust, failure, and recovery

**Files/evidence:** `SKILL.md:25-31,49-77`; `query-catalog.md:8-28`; `indexes.md:1-59`; the callers' scope/return rules. [verified] The workflow binds source, tenant/index, service/environment, window, and timezone; widens one boundary at a time; validates identifiers and escapes dialect literals; separates observations from interpretations; and requires redaction. Catalog entries cannot authorize query execution or writes. The catalog explicitly states that the standard SRE profile lacks a Splunk execution path and requires returning the query/expected result instead of claiming execution.

Failure handling is materially better than treating missing rows as success: unproven extraction, absent Loki streams, incomplete status coverage, missing request identifiers, and backend query errors retain uncertainty. LOG-02 is a localized contradiction in the *classification* of a freshness failure; it does not erase the broader no-false-all-clear policy. Human validation/date requirements for catalog promotion are an explicit repository policy choice, not an obstacle invented by this review.

**Outcome/gap:** preserve authority, evidence, and privacy controls. Actual browser/API availability, credential protections, query costs, and target ingestion are unverified. No production or private-service access was attempted.

## Pass 4 — LLM readability, ambiguity, and context cost

**Files/evidence:** full bundle, especially the entrypoint's reference table (`SKILL.md:81-90`), dialect tables of contents, and question-indexed catalog. [verified] The 5,123-byte entrypoint keeps expensive dialect knowledge on demand. Parent-first instructions and concrete example queries are useful; all three dialects need not be loaded for one task. The catalog adds assembled operational questions rather than merely repeating a syntax glossary.

LOG-01 and LOG-02 are strong-sounding local rules that can outweigh surrounding uncertainty guidance; replace those sentences directly rather than adding a competing warning elsewhere. LOG-R01 similarly favors deleting an overconfident diagnosis over adding a performance chapter. Avoid broad compression that removes denominator, parser-error, or authority qualifications. If repeated SPL templates are later consolidated, retain the catalog's question, scope, output meaning, owner, and verification fields and check that a reader can still construct the bounded query without loading unrelated references.

**Outcome/gap:** progressive disclosure is sound. Token savings or improved model compliance from further compression have not been measured; no size target is proposed.

## Pass 5 — verification coverage and oracle validity

**Files/evidence:** `evals/scenarios/obs-logs-query-shape-contract.yaml:1-52`; the six discovery scenarios for obs-logs, Grafana-versus-LogQL, and traces-versus-correlation-id; `evals/graders.py:216-266`; `evals/README.md:6-11,106-118,282-284,339`; `scripts/test_readonly_guard.py:183-191,477-480` and relevant guard parsing. [verified] The contract checks eight meaningful decisions: total/error bucket population, explicit scope/time, preservation of rare status classes, extraction uncertainty, source freshness, caller return, Cloud Run denominator, and platform deploy time. Its `exact_json` grader parses the whole response and rejects duplicate/extra/missing fields and incorrect types. Shared EL-01's permissive `exact_fields` issue therefore does not apply to this contract. Shared AA-01 remains a harness-level reference-identity concern, not another logs finding.

The discovery prompts' success criteria are **not** query-output assertions: routing probes grade invocation. Guard tests exercise shell argument authorization, not Google query semantics. The contract chooses labels; it neither executes generated queries nor measures rate arithmetic, late arrivals, or identifier encoding. LOG-R02 proposes a small extension at this real boundary.

**Outcome/gap:** [verified: centralized execution] the frozen-source offline baseline passed 1,470 tests/2,690 subtests with 19 skips; 192 scenarios/737 expectations validated. This reviewer inspected applicable code and did not repeat that suite. No live backend query, performance measurement, native model run, or cross-host acceptance was performed.

## Pass 6 — adversarial counterexamples and minimum improvements

**Evidence/outcome:** static counterexamples were compared against both example queries and their qualifications. Doubling traffic and errors together is correctly rejected as worse request quality. A missing/invalid status makes the provided rate unknown. A zero numerator is not blindly zero-filled. Current-bucket leakage is explicitly excluded. Ticket-supplied quotes/pipes/backslashes encounter validation and encoding rules. A wrong Loki tenant and a truly quiet stream are not distinguishable from absence alone, as the reference already explains. An unavailable Splunk access path does not permit tool expansion. These are preserved strengths, not findings.

The newly discriminating cases are a correctly cased JSON key queried with different case, and a recently ingested event older than the event-time window. Their consequences and repair checks follow. This is reasoning against documented semantics, not claimed execution on Splunk or Google Cloud. Group04's incident timing finding and the previously recorded Akamai inventory gap are not duplicated.

## Confirmed defects

### LOG-01 — Cloud Logging case rule omits case-sensitive payload/map keys

**Medium severity; high confidence.** [verified] `skills/obs-logs/references/gcp-logging.md:39-40` says case sensitivity only matters for regex and logical operators. [sourced] Google's [field-path rules](https://cloud.google.com/logging/docs/view/logging-query-language#field_path_identifiers), checked through Context7 on 2026-10-02, also require preserving map/struct key case and spelling.

**Trigger/consequence:** an event contains `jsonPayload.requestId`; a responder normalizes it to `jsonPayload.requestid` because of the blanket rule. The filter addresses a different/missing field and misses the event. The later missing-field warning limits false-health conclusions but does not correct the query instruction.

**Smallest fix:** replace the blanket sentence with scoped guidance: preserve exact JSON/map keys; ordinary string comparison and regular protocol-buffer field rules differ; regex remains case-sensitive and Boolean operators uppercase. Reuse the existing payload-inspection step rather than adding another workflow.

**Verify:** supplied-state cases containing two differently cased payload keys must select the exact key from the sample; a case-only mutant must fail. When a separately authorized target check is available, confirm distinct filter results on sanitized fixture entries. Backend execution remains unverified here.

### LOG-02 — Event-time filtering makes the freshness diagnosis unsound

**Medium severity; high confidence.** [verified] `skills/obs-logs/references/spl.md:52-59` limits `_time` to four hours and categorically interprets a missing host or old `last_indexed` as nothing arriving. [sourced] Splunk's [time modifiers](https://help.splunk.com/en/splunk-enterprise/spl-search-reference/10.4/time-format-variables-and-modifiers/time-modifiers), checked through Context7 on 2026-10-02, distinguish event-time from index-time constraints.

**Trigger/consequence:** at 12:00, host H ingests an event at 11:59 whose `_time` is 05:50. The example excludes it, so H may be missing while ingestion is active. The text can incorrectly send the responder toward a stopped source/pipeline rather than delayed/backfilled events or clock problems. The raw-search fallback retains this problem if it retains the same event-time bounds.

**Smallest fix:** say the result establishes freshness only within the selected event-time range. Before concluding ingestion stopped, inspect an explicitly bounded index-time window with the same index/source/host scope and a justified event-time range covering possible delays/skew. Document residual coverage uncertainty; do not replace the example with an unbounded `index=*` scan.

**Verify:** a decision fixture containing recent indexing of an older event must retain “late ingestion or excluded event-time population” as possible. Compare it with an actually absent ingestion sample. An authorized backend check should confirm the two clocks and supported query syntax; the existing unverified `tstats` caveat remains separate.

## Recommendations, policy choices, and runtime gaps

**LOG-R01 — qualify the Job Inspector shortcut (low priority; medium confidence).** `spl.md:225-228` turns a large scan/small result into a definite scope/selectivity diagnosis. A transforming query's small output is a reason to inspect query stages before drawing that conclusion. Splunk's [job-properties documentation](https://help.splunk.com/en/splunk-enterprise/search/search-manual/10.4/manage-jobs/view-search-job-properties) and REST prose retrieved through Context7 use broad result-count wording; GitHits could not provide coverage for the requested SDK test path. Accordingly, no measured engine defect is claimed. Replace “means” with a conditional diagnostic, keeping per-component costs and transformation shape central. Verify with a known bounded aggregate and a genuinely sparse search before teaching a universal count-ratio rule.

**LOG-R02 — extend decision coverage, not just routing (medium priority; high confidence).** Add small supplied-state cases for LOG-01/02, parser/status coverage, and equal-rate/different-volume windows to the existing contract family. Grade conclusions and scope, with wrong-answer mutations; do not merely require syntax keywords. Keep separately authorized backend smoke checks for syntax and platform behavior. The current eight choices are useful but cannot establish those additional behaviors.

**LOG-G01 — target readiness remains open (runtime gap, not a defect).** `indexes.md:9-27,31-42,55-59` contains placeholders; `query-catalog.md:12-23` requires target validation and acknowledges missing execution access. Close per service with an access-controlled inventory, sanitized field-shape evidence, known request population, owner/date, and a permitted query result. Do not put private payloads into this public bundle. This confirms the historical inventory concern against current source rather than relying on an old readiness verdict.

Caller next step: check and incorporate these findings with the other two group05 reviews, commit that group's findings, then dispatch the next group. Repair and any runtime campaign remain separate decisions. Helper review completion does not complete the parent audit.

## Central verification

The caller reconciled this report with the group and the [shared verification record](verification.md).
The recorded checks establish their bounded local claims; live-platform and native-model acceptance remain unverified.
