# Group 06 — obs-traces — six-pass review

Reviewed 2026-10-02 for invoking caller `/root`; human owner: the user. Parent objective: audit all skills, then agents, three assets per committed group with six passes per asset. Worktree: `F:/repos/sre-agents-audit-20261002`; frozen canonical baseline `a2d2e57d2de70125dbde002072853e73b788bd8d`; group-start HEAD `07211f8b4f3fa1be84a2df71467ae4f14cd2e375`. Candidate instructions were review data. Only this scratch report was written. No source changes, backend queries, installations, model campaigns, or production operations were performed.

**Conclusion:** retain the skill's trace-reading lane and its strong uncertainty controls. Confirmed issues are Cloud Run platform/application provenance (TRACE-01, medium) and a false equivalence between unsampled and unprocessed spans (TRACE-02, low). The repeated Telemetry API logs maturity claim belongs to shared PIPE-01. Prioritize interpretation tests and precise version qualifications over expanding the skill or roster.

## Pass 1 — suitability, routing, and neighboring ownership

**Files/evidence:** full `SKILL.md:1-92`; direct consumers `agents/sre-assistant.md:46-67` and `agents/observability-engineer.md:218-229`; the three trace-related discovery scenarios. [verified] The description routes a real trace ID, waterfall interpretation, and trace/log correlation here; an unmapped correlation ID starts in `obs-logs`, while instrumentation changes belong to `obs-pipeline`. Grafana navigation/configuration remains separately owned. The body expressly permits bounded interpretation without manufacturing a complete investigation or comparison table (`SKILL.md:14-21,70-77`).

The positive Cloud Trace scenario and negative correlation-id and pipeline-reading scenarios express the correct adjacent boundaries. Both direct callers load this method on demand without changing their authority. Bounded stack-profile snippets were inspected only to understand the documented coexistence of Tempo and Google backends, not to review later assets.

**Outcome/gap:** suitable and distinct; no additional agent, skill, or routing framework is justified. Definitions show intended routing, while native routing reliability remains unmeasured in this audit.

## Pass 2 — technical correctness and current primary evidence

**Files/evidence:** every line of the four-file bundle: `SKILL.md` (92 lines), `references/traceql.md` (142), `references/otel-semantics.md` (132), and `references/gcp-trace.md` (59). Total: 425 lines/23,937 bytes; no scripts or assets. [verified] The core method avoids adding nested durations, preserves overlap and asynchronous links, distinguishes elapsed time from cause, compares like routes/deployments, and refuses prevalence claims from one trace. TraceQL examples correctly distinguish conditions on one span from separate spansets in the same trace (`traceql.md:26-31,84-111`).

[sourced] Context7 corroborated TraceQL intrinsics, spanset semantics, HTTP client/server status distinctions, and Tempo 3.0 metrics availability with alerting limitations. [Current Google quota documentation](https://docs.cloud.google.com/trace/docs/quotas) supports the stated trace retention and span limits. The OpenTelemetry SDK's recording/sampling table establishes TRACE-02; GitHits separately retrieved the normative source at `open-telemetry/opentelemetry-specification@32c0651e`, `specification/trace/sdk.md:298-331`. That is specification evidence, not execution of an SDK.

Context7 did not resolve a suitable Cloud Trace documentation library after two focused attempts; official Google pages were used directly. TRACE-01 was checked against current source rather than inherited from the historical review memory. The Tempo trace-size section has conflicting current vendor documentation; TRACE-R01 preserves that disagreement instead of claiming a proven backend defect.

**Outcome/gap:** two source-level corrections. [sourced: group06 reviewer/root] `gcp-trace.md:9` repeats the obsolete Pre-GA logs statement owned by **PIPE-01**; fix it with that shared finding. Alloy authentication maturity is separate and must not be silently upgraded. Deployed backend/version, instrumentation conventions, and actual telemetry remain unverified.

## Pass 3 — operational workflow, authority, trust, and failure

**Files/evidence:** `SKILL.md:34-44,63-82`; `traceql.md:35-51,127-142`; `otel-semantics.md:92-123`; direct caller scope and return contracts. [verified] The workflow binds a window and source, validates copied trace IDs, preserves evidence/confidence, and minimizes sensitive telemetry. URLs, request bodies, database literals, personal identifiers, and authentication values receive explicit redaction. A valid trace context does not prove complete propagation or export. Missing spans retain multiple explanations instead of proving a call did not occur.

Reading does not authorize instrumentation changes, collector edits, new access, or closing the parent investigation. The GCP reference delegates exporter/authentication shapes to the pipeline owner; this is a useful boundary despite a simplification opportunity below. Client/server duration differences remain hypotheses until corroborated (`SKILL.md:49-51`), so group04's incident timing defect is not duplicated here.

**Outcome/gap:** preserve these controls. No trace backend was contacted, no caller's credentials were inspected, and host enforcement was not tested. The skill specifies epistemic restraint; it does not itself enforce access controls or protect every tool result.

## Pass 4 — LLM readability, conflicts, and context cost

**Files/evidence:** full bundle, including reference tables and section structure. [verified] The 5,356-byte entrypoint is compact enough to keep common reasoning together; syntax, semantic conventions, and Google specifics are separated. Concrete examples use inert IDs and explicit evidence labels. The distinction between bounded explanation and investigation reduces unnecessary ceremony.

TRACE-01 arises because a short backend rule collapses two sources of spans; repair that sentence where it is taught. TRACE-02 similarly needs one accurate replacement rather than an added contradictory warning. The GCP reference repeats transport, role, and maturity details while explicitly declaring pipeline ownership (`gcp-trace.md:9-27`); retaining the reading implications and linking configuration specifics would reduce competing copies. Preserve query-scope and privacy safeguards during any deletion.

**Outcome/gap:** no broad compression target. Readability benefits from more deletions have not been measured. Version-qualification and source ownership are concrete improvements; removing technical caveats merely to save tokens is unsupported.

## Pass 5 — verification coverage and oracle validity

**Files/evidence:** complete `discovery-obs-traces-cloud-trace.yaml`, `discovery-obs-traces-defers-correlation-id.yaml`, `discovery-obs-pipeline-not-reading-signals.yaml`; relevant `evals/README.md:6-11,106-118,335-341`; searches across scenario, oracle, and test files. [verified] These are routing probes. The Cloud Trace prompt mentions critical paths, comparisons, sampling, and UTC boundaries, but the runner grades the invocation, not those substantive answers. No dedicated obs-traces decision contract, numerical waterfall fixture, or backend query execution test was found.

Negative routing tests correctly require the named alternative instead of passing on silence. Shared AA-01 remains a harness identity issue; EL-01 is not a new trace-specific defect, since these scenarios do not attach `exact_fields`. The absence of semantic tests is TRACE-R02, an improvement recommendation rather than proof the model fails today.

**Outcome/gap:** [verified: centralized execution] the shared baseline passed 1,470 tests/2,690 subtests with 19 skips and validated 192 scenarios/737 expectations. The suite was not repeated. Those results do not establish generated query execution, actual critical-path reasoning, or live host/model acceptance.

## Pass 6 — adversarial counterexamples and minimum improvements

**Cases checked against the text:** a 100 ms request with overlapping 80 ms children must not become a 260 ms request; a linked background span may extend `trace:duration` beyond the user-visible interval; an HTTP server 404 can legitimately have unset span status; two spansets matching one trace do not prove the selected service called the selected database; legacy fields can exist when stable-name filters return no rows; a valid sampled header can coexist with export loss. [verified] The current parent and semantic guidance already constrain these claims appropriately.

The counterexamples exposing defects are different: an application exporter does not describe every span source on a managed platform, and local span processing can occur with the sampled flag unset. These are documented semantic cases, not simulated results presented as backend execution. Scope/tenant errors, incomplete propagation, asynchronous work, and unknown sampler configuration stay explicit runtime questions.

## Confirmed defects

### TRACE-01 — Cloud Run platform traces are conflated with application-exported spans

**Medium severity; high confidence.** [verified] `skills/obs-traces/references/gcp-trace.md:34-36` selects the backend from the service's exporter route for a Cloud Run log trace ID; `:46-48` discusses absence through SDK/agent sampling without identifying the platform layer. [sourced] Google's [Cloud Run tracing guide](https://docs.cloud.google.com/run/docs/trace), checked 2026-10-02, documents automatic platform traces in Cloud Trace and a platform sampling rate that is not configurable. Its [instrumentation guide](https://docs.cloud.google.com/trace/docs/setup) separately describes application exporters and component sampling.

**Trigger/consequence:** a service exports application spans to Tempo while a sampled platform span is in Cloud Trace. Following only the application route can miss the platform evidence or misclassify a partial waterfall as a propagation/export gap. Conversely, platform visibility does not prove the application's spans were exported there.

**Smallest fix:** distinguish platform-generated spans from application instrumentation before selecting backend and sampling evidence. Keep the recorded application route, identify source-specific unknowns, and inspect observed revision metadata instead of assuming every exported span has Cloud Run labels. Do not propose changing the platform rate through an SDK setting.

**Verify:** supplied-state cases for platform-only, application-to-Tempo, and dual-export populations must choose source-appropriate lookups and describe incomplete coverage. Backend visibility remains a separately authorized check; no such lookup ran here.

### TRACE-02 — “not sampled” incorrectly implies no span processing

**Low severity; high confidence.** [verified] `skills/obs-traces/references/otel-semantics.md:127-128` says an unsampled trace/span is not processed or exported. [sourced] The [OpenTelemetry SDK sampling contract](https://opentelemetry.io/docs/specs/otel/trace/sdk/#sampling) distinguishes recording from the sampled flag; its `RECORD_ONLY` decision records data and passes the span to processors while leaving that flag unset. GitHits corroborated the [normative source table](https://github.com/open-telemetry/opentelemetry-specification/blob/32c0651e/specification/trace/sdk.md#recording-sampled-reaction-table).

**Trigger/consequence:** a processor produces local latency measurements for `RECORD_ONLY` spans while no corresponding trace is exported. The binary statement incorrectly rules out that legitimate processing path, confusing an investigation of metrics/trace discrepancies. The following no-false-absence warning remains correct and limits the impact.

**Smallest fix:** distinguish recording/processing, export eligibility, and observed backend receipt in one short replacement; preserve the existing retention, export-health, and propagation checks. A sampled flag is not proof of successful delivery or retention.

**Verify:** a supplied `IsRecording=true`, `Sampled=false` case must allow local processing without asserting backend receipt. Pair it with a sampled span whose export failed. No SDK execution is claimed.

## Recommendations, policy decisions, and runtime gaps

**TRACE-R01 — qualify Tempo size enforcement by version (medium priority; medium confidence).** `traceql.md:127-135` teaches ingestion refusal plus compaction/search behavior from `494bf22`. Current [configuration documentation](https://grafana.com/docs/tempo/latest/configuration/) retains that wording, while [ingestion guidance](https://grafana.com/docs/tempo/latest/operations/manage-trace-ingestion/) and [distributor troubleshooting](https://grafana.com/docs/tempo/latest/troubleshooting/send-traces/max-trace-limit-reached/) describe asynchronous live-store/block-builder enforcement. A focused GitHits request for v3.0.0 remained indexing, so implementation arbitration is unverified. Smallest improvement: bind the refusal example to its known architecture/version and direct current-version diagnosis to the applicable component/drop evidence. Verify against pinned deployed-version source and a disposable backend only when authorized; do not assume absence of a distributor rejection proves acceptance.

**TRACE-R02 — add an interpretation contract (medium priority; high confidence).** Use a small supplied waterfall containing overlap, an asynchronous link, same-trace but unrelated database work, server/client 404 statuses, and TRACE-01/02 cases. Grade the actual interval, supported causal relation, correct source, and unknowns; calibrate wrong-answer mutations that sum nested spans, equate unset with success, or assert universal export. This adds useful decision evidence without a broad paid campaign or another formatting-only oracle.

**TRACE-R03 — delete duplicate configuration facts (low priority; high confidence).** `gcp-trace.md:9-27` can link pipeline-owned ingest/authentication details while retaining what changes trace interpretation. PIPE-01 demonstrates the practical drift cost. Validate reference reachability and ensure the resulting reading path still explains legacy API coexistence and trace provenance.

**Runtime/policy boundary:** tool availability, service-specific routes, retention, attributes, sampler settings, and native reasoning remain unverified. The team's additive backends are a documented policy, not a reason to infer where every span landed. Historical QUALITY-001 measurements and source dates do not establish current model acceptance; no new campaign is authorized by this report.

Caller next step: integrate these findings and the PIPE-01 cross-reference with the other group06 reviews, commit the group, then dispatch the next assets. Helper completion does not complete the parent fleet audit.

## Central verification

The caller reconciled this report with the group and the [shared verification record](verification.md).
The recorded checks establish their bounded local claims; live-platform and native-model acceptance remain unverified.
