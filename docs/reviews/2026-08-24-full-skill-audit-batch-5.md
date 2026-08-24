# Full skill audit — Batch 5 of 6

Date: 2026-08-24  
Scope: `obs-pipeline`, `akamai-edge`, `gcp-ops`, `pcf-ops`, `stack-profile`  
Baseline commit ID: `79916945d7108309567275c40906d47ecd6d6b74`
Method: Baseline → Inspect → Research → Change → Validate → Compare

## Executive conclusion

These five skills form the fleet's runtime and telemetry boundary: `stack-profile` supplies current
facts, `pcf-ops` and `gcp-ops` own application-side triage on the two coexisting runtimes,
`akamai-edge` owns the customer-configurable edge surface, and `obs-pipeline` owns signal delivery.
The lane split is coherent and the supporting references are loaded conditionally.

The audit found seven execution-relevant defects:

1. `docs/rules.md` contradicted the canonical `stack-profile`: it said GCP was not a target and
   prohibited all managed cloud services even though the approved GCP migration is in progress.
2. `gcp-ops` said Cloud Run traffic routes to the latest healthy revision by default without
   preserving existing traffic splits, prior-revision assignments, `--no-traffic`, or the difference
   between staged `--to-revisions` assignment and a 100% `--to-latest` restoration.
3. The Alloy reference named Application Default Credentials but omitted the executable
   `otelcol.auth.google` configuration and the public-preview stability flag.
4. The pipeline entrypoint described all three Google Telemetry API signals without saying that logs
   ingestion is Pre-GA.
5. The Akamai reference flattened two conflicting vendor retry descriptions into one exact budget,
   making a disputed delivery-loss threshold look settled.
6. The Akamai reference gave one exact Traffic report decommission date even though the vendor's
   planning changelog and current report page differ by one day.
7. The PCF router reference called 90 seconds a generic Gorouter keepalive instead of scoping it to
   the upstream backend-connection idle timeout and distinguishing the configurable frontend timeout.

The smallest effective corrections are implemented. The version-only Alloy and OpenTelemetry Java
labels were also changed from moving “current” claims to dated review anchors. No skill description,
agent, delegation edge, production authority, dependency, schema, or generated projection changed in
this batch.

## Method and evidence

### Local baseline

- `[verified]` The baseline contains 30 canonical skill entrypoints. The five Batch 5 bundles contain
  20 tracked files totaling 86,036 Git blob bytes: five entrypoints, 13 references, and two
  human-run triage scripts.
- `[verified]` Every file in all five bundles was inspected in full. Every supporting resource is
  reachable from its owning `SKILL.md`; no generated projection was treated as a source.
- `[verified]` `docs/fleet-roadmap.md` was checked as the only live backlog. Its existing
  `stack-profile` routing closeout does not authorize a new restructure or historical GCP work.
- `[verified]` Before correction, all 5 initial platform-contract regressions failed: stale GCP
  policy, incomplete Cloud Run traffic semantics, flattened Akamai retry behavior, wrong Akamai
  date disagreement, and incomplete Alloy Google authentication/lifecycle guidance.
- `[verified]` A sixth focused regression then failed on the moving OpenTelemetry Java “current
  release” label and passed after it became a dated review anchor.
- `[verified]` Independent review added two decision-critical red cases: Cloud Run traffic guidance
  lacked the staged-assignment branch, and the Gorouter 90-second statement did not name the backend
  idle-connection scope. Both failed before their corrections and pass afterward.
- `[verified]` Existing discovery scenarios cover seven Akamai boundaries, seven GCP boundaries,
  and one runtime-profile boundary. There is no direct `obs-pipeline` discovery case and no primary
  `pcf-ops` discovery case.

### Current primary documentation via Context7

Context7 established documented contracts and remained separate from private-checkout inspection:

- `[sourced]` Alloy documents the OTLP receiver/batch/export shape, `alloy validate`, HTTP readiness,
  remote-write buffering, and component-level retry/loss behavior:
  [Alloy OTLP receiver](https://grafana.com/docs/alloy/latest/reference/components/otelcol/otelcol.receiver.otlp/),
  [OTLP exporter](https://grafana.com/docs/alloy/latest/reference/components/otelcol/otelcol.exporter.otlp/),
  and [validate](https://grafana.com/docs/alloy/latest/reference/cli/validate/).
- `[sourced]` OpenTelemetry defines portable metric naming, stable
  `deployment.environment.name`, Java agent-versus-starter selection, and the stateful tail-sampling
  requirement that all spans for a trace reach the same sampling collector:
  [metric API](https://opentelemetry.io/docs/specs/otel/metrics/api/),
  [resource semantic conventions](https://opentelemetry.io/docs/specs/semconv/resource/deployment-environment/),
  and [Java zero-code instrumentation](https://opentelemetry.io/docs/zero-code/java/).
- `[sourced]` Cloud Foundry documents application liveness/readiness semantics, the exact-HTTP-200
  health contract, application events, logs, environment groups, and app-side versus platform-side
  triage surfaces:
  [health checks](https://docs.cloudfoundry.org/devguide/deploy-apps/healthchecks.html) and
  [`cf` CLI reference](https://cli.cloudfoundry.org/en-US/v8/).
- `[sourced]` The Akamai CLI documentation supports the local use of error-string translation,
  URL health, property inspection, activation, and rollback-oriented operations. Portal-only and
  lifecycle facts were checked against Akamai's current primary pages separately.

### Current upstream implementation and release evidence via GitHits

GitHits was used for public source, release, and default-value evidence; it did not inspect the
private checkout:

- `[sourced]` Alloy v1.18.1 is the latest release reviewed in this batch. Current source confirms
  that `otelcol.receiver.otlp` starts no transport unless configured, the OTLP exporter discards a
  failed batch after its retry window, the default sending queue is in-memory, remote-write WAL
  retention can still lose old unsent samples, and `loki.write` counts data dropped after retries:
  [Alloy releases](https://github.com/grafana/alloy/releases),
  [OTLP exporter source documentation](https://github.com/grafana/alloy/tree/main/docs/sources/reference/components/otelcol),
  and [`loki.write` source documentation](https://github.com/grafana/alloy/blob/main/docs/sources/reference/components/loki/loki.write.md).
- `[sourced]` OpenTelemetry Java instrumentation 2.31.1 was published on 2026-08-23. Current source
  supports Java 8+, with individual instrumentations allowed to require newer Java:
  [2.31.1 release](https://github.com/open-telemetry/opentelemetry-java-instrumentation/releases/tag/v2.31.1)
  and [Java instrumentation README](https://github.com/open-telemetry/opentelemetry-java-instrumentation/blob/main/README.md).
- `[sourced]` Current semantic-conventions source marks `deployment.environment.name` stable and
  the old `deployment.environment` deprecated. Current collector-contrib source keeps tail sampling
  beta/stateful, with a 30-second decision wait, 50,000-trace capacity, no default policy, and
  unmatched traces unsampled:
  [deployment attributes](https://github.com/open-telemetry/semantic-conventions/blob/main/docs/registry/attributes/deployment.md)
  and [tail-sampling processor](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/processor/tailsamplingprocessor).
- `[sourced]` Current upstream Gorouter source uses 90 seconds for the backend HTTP transport's
  idle-connection timeout; the frontend server timeout is configured separately:
  [backend transport](https://github.com/cloudfoundry/gorouter/blob/main/proxy/proxy.go) and
  [frontend server](https://github.com/cloudfoundry/gorouter/blob/main/router/router.go).

### Current official vendor documentation

Official vendor pages were required for current surfaces not indexed deeply enough by Context7 or
GitHits:

- `[sourced]` Grafana documents `otelcol.auth.google` as public preview, requiring
  `--stability.level=public-preview` or lower and exporting an ADC-backed authentication handler:
  [`otelcol.auth.google`](https://grafana.com/docs/alloy/latest/reference/components/otelcol/otelcol.auth.google/).
- `[sourced]` Google documents `telemetry.googleapis.com` for OTLP logs, metrics, and traces, but
  marks logs ingestion Pre-GA:
  [OTLP log ingestion](https://docs.cloud.google.com/stackdriver/docs/otlp-logs/overview).
- `[sourced]` Cloud Run documents immutable revisions, persistent traffic splits, `--no-traffic`,
  `--to-latest`, revision rollback, direct VPC subnet sizing, multi-container startup order, memory
  behavior, and Preview domain mappings:
  [traffic management](https://docs.cloud.google.com/run/docs/rollouts-rollbacks-traffic-migration),
  [direct VPC egress](https://docs.cloud.google.com/run/docs/configuring/vpc-direct-vpc), and
  [container contract](https://docs.cloud.google.com/run/docs/container-contract).
- `[sourced]` Akamai's planning changelog gives 2025-11-05 as the Traffic report change date while
  the current report page says 2025-11-06. Its DataStream FAQ and troubleshooting page also disagree
  on the precise 429/5xx retry count:
  [decommission plan](https://techdocs.akamai.com/reporting/changelog/apr-24-2025-traffic-and-todays-traffic-reports-decommission),
  [current Traffic report page](https://techdocs.akamai.com/reporting/docs/traffic-rpts),
  [DataStream FAQ](https://techdocs.akamai.com/datastream2/v2/docs/faq), and
  [DataStream troubleshooting](https://techdocs.akamai.com/datastream2/docs/troubleshooting).

### Provenance disagreements retained

- Akamai's FAQ says 429/5xx delivery gets up to 10 attempts within five minutes; its
  troubleshooting page says log data may be lost after three unsuccessful retries. The skill now
  preserves the disagreement and labels the exact per-failure budget `[unverified]`; it retains the
  common operational conclusion that there is no backup copy.
- Akamai's decommission planning changelog says the Traffic report change was effective November 5,
  while the live report page records November 6. The skill preserves both dates, labels the exact
  effective day `[unverified]`, and relies only on the undisputed replacement.
- Alloy's documented Google authentication component is usable but public preview. Google's OTLP
  endpoint accepts all three signals, while logs ingestion has a separate Pre-GA lifecycle. The
  skill no longer turns either upstream capability into target-deployment proof.
- GitHits confirms v1.18.1 and Java instrumentation 2.31.1 as current releases on the review date,
  but moving “current” labels do not improve execution. The references retain dated review anchors
  and still require target-version inspection.

---

## Skill: obs-pipeline

### Overall Assessment

**Significant Changes**

### Purpose

Designs and validates end-to-end telemetry delivery from application instrumentation through
Alloy/OpenTelemetry processing to signal backends, with explicit cardinality, naming, loss, and
canary evidence.

### Findings

- **Routing:** The description owns instrumentation, collectors, routing, schema, cardinality, and
  missing-signal diagnosis. Query construction remains with the signal skills, alert policy with
  `obs-alerting`, and active incidents with `sre`. No description change was needed.
- **Instructions:** The application → SDK/agent → collector → backend boundary walk is concise and
  executable. The GCP paragraph named the endpoint and ADC but did not supply the auth component or
  the stability flag required to load it.
- **Accuracy:** Current Alloy and Google documentation support the OTLP shape. Logs have a different
  Pre-GA lifecycle, and `otelcol.auth.google` is public preview; those qualifiers are now explicit.
  Current OTel source supports the naming, resource, agent/starter, and tail-sampling rules.
- **Context:** The 6.1 KB entrypoint carries signal-independent rules. The larger Alloy and OTel SDK
  references load only for collector or instrumentation work. The split is effective progressive
  disclosure and should not be flattened.
- **References / Assets / Scripts:** Two references cleanly separate application instrumentation
  from Alloy routing. No deterministic script is needed because validation must use the target
  config/version and an end-to-end canary.
- **Tools:** The skill names target inspection, syntax validation, health endpoints, internal
  dropped/refused/failed metrics, and backend queries. It does not convert documented commands into
  authority to alter a live collector.
- **Orchestration:** Application code changes go to `sde`; steady-state pipeline config stays with
  `observability-engineer`; query verification comes from the signal skills; active impact stays with
  `sre`. The packet preserves exact target, version, route, and signal evidence.
- **Failure Handling:** Missing receivers, wrong wiring exports, batch/queue exhaustion, WAL
  truncation, retry exhaustion, cardinality explosion, secret/PII leakage, and broken correlation
  are distinct failure states. The GCP route now also fails closed on missing preview enablement.
- **Verification:** The new regression asserts executable Google auth syntax, the public-preview
  flag, ADC, Pre-GA logs, and dated version wording. Live target config, permissions, and canary
  remain correctly `[unverified]`.
- **Portability:** OTLP, OTel resources, RED/USE, W3C trace context, cardinality, and end-to-end
  canaries are portable. Alloy components, stability flags, and Google endpoints are vendor-specific
  and isolated in the reference.

### Routing Tests

#### Should trigger

1. “Instrument this Spring Boot service with OpenTelemetry without loading both the agent and starter.”
2. “Build an Alloy OTLP route from the app to Tempo and explain where spans can be dropped.”
3. “Our metrics arrive but traces do not; walk every telemetry boundary and design a canary.”

#### Should not trigger

1. “Write the PromQL for checkout p95 latency” — `obs-metrics` owns the query.
2. “Design the page threshold and notification route” — `obs-alerting` owns alert policy.
3. “The service is down right now; coordinate the incident” — `sre` owns active impact.

#### Boundary cases

1. “Cloud Trace has no spans for the service” — use this skill for instrumentation/export-path
   evidence; use `obs-traces` only after trace data exists to interpret.
2. “Add a Grafana panel for collector drops” — this skill supplies the verified signal and loss
   semantics; `obs-dashboards` owns the panel.

### Recommended Changes

#### Change 1 — make Google OTLP authentication executable and lifecycle-correct

- **Problem:** The reference named ADC but left the exporter auth block unverified and omitted the
  flag required to enable the component.
- **Evidence:** Grafana's current primary documentation provides the exact
  `otelcol.auth.google.<label>.handler` wiring and marks the component public preview; Google marks
  OTLP logs ingestion Pre-GA.
- **Change:** Add the smallest documented exporter/auth example, the stability flag, and separate
  component/signal lifecycle qualifiers. Keep project, permission, flag adoption, and canary target
  evidence unverified.
- **Expected improvement:** A model can produce a syntactically grounded candidate without silently
  assuming the component is stable or logs are GA.
- **Risk/tradeoff:** Public-preview syntax can change; the dated source and deployed-version check
  remain load-bearing.

#### Change 2 — replace moving current-version labels with dated review anchors

- **Problem:** “Current stable” and “current release” drift even when the instruction remains valid.
- **Evidence:** GitHits confirmed Alloy 1.18.1 and OTel Java instrumentation 2.31.1 on the review
  date, but neither version selects a target deployment automatically.
- **Change:** Say the guidance was reviewed against those versions on explicit dates.
- **Expected improvement:** Retains reproducibility without turning an upstream release pointer into
  a stale target assumption.
- **Risk/tradeoff:** Future readers must re-check newer release notes when using version-gated syntax;
  that was already required.

### Keep As-Is

Keep the boundary-by-boundary missing-signal method, bounded-cardinality contract, OTel naming rules,
agent-versus-starter decision, stateful tail-sampling warnings, failure metrics, and end-to-end canary.
They are high-signal safeguards and belong in the current progressive structure.

---

## Skill: akamai-edge

### Overall Assessment

**Minor Changes**

### Purpose

Separates edge-versus-origin triage, team-owned property/security configuration, and mPulse real-user
evidence while preserving Akamai's platform boundary and change authority.

### Findings

- **Routing:** The description covers reference strings, cache/WAF evidence, property versions,
  activation/fallback, and mPulse. Seven discovery scenarios exercise adjacent log, metric, trace,
  alert, PCF, and active-incident deferrals. No routing edit was needed.
- **Instructions:** The first-question evidence tree and three authority postures are compact and
  operationally useful. Each lane points to one focused reference.
- **Accuracy:** Current vendor pages support the diagnostic tools, Enhanced Debug, latency-profile
  tradeoff, property activation, mPulse INP, and Reporting API. Neither the retry budget nor the
  exact Traffic report date has one consistent vendor statement; both disagreements are preserved.
- **Context:** The entrypoint remains small while three references isolate triage, property changes,
  and RUM. The duplication between one-request diagnostics and fleet-wide logs is intentional
  escalation, not redundant prose.
- **References / Assets / Scripts:** No script is appropriate for account-bound portal evidence or
  activation authority. Exact fields, timings, and commands stay close to their vendor surfaces.
- **Tools:** Portal/API reads, human-recommended debug probes, reviewable property diffs, and
  staging-first activation are distinguished. The skill never implies authority over Akamai's edge
  platform.
- **Orchestration:** Backend log queries come from `obs-logs`; trend metrics from `obs-metrics`;
  app traces from `obs-traces`; active incidents from `sre`; property/security writes remain with
  named human owners.
- **Failure Handling:** Sampling windows, delayed/incomplete streams, delivery loss, custom WAF deny
  responses, missing debug support, activation timing, and rollback eligibility are explicit.
  Missing DataStream records no longer inherit a falsely precise retry guarantee.
- **Verification:** The focused regression requires both vendor dates plus an unverified exact-day
  label, and requires the retry disagreement, exact-budget uncertainty, and no-backup conclusion to
  coexist. No account or property was queried or changed.
- **Portability:** Edge/origin isolation and RUM slicing are portable. Akamai headers, portal tools,
  report names, activation timings, and fast fallback are vendor-specific.

### Routing Tests

#### Should trigger

1. “Decode this Akamai Reference #9 error and decide whether the failure is edge or origin.”
2. “Review this Property Manager change and plan a staging-first activation with rollback.”
3. “mPulse shows slower pages in one geography; separate network time from front-end time.”

#### Should not trigger

1. “Search the application logs for this request ID” — `obs-logs` owns the backend query.
2. “The checkout service is failing for users right now” — `sre` owns active impact.
3. “Investigate a Cloud Foundry container crash” — `pcf-ops` owns app-runtime triage.

#### Boundary cases

1. “The WAF may be blocking users” — use this skill for sampled Akamai security evidence; the human
   security owner decides any policy change.
2. “DataStream shows higher origin time after a property activation” — this skill owns edge/change
   correlation; hand verified origin evidence to the application/runtime lane without claiming cause.

### Recommended Changes

#### Change 1 — preserve Akamai's retry-documentation disagreement

- **Problem:** One local sentence chose the FAQ's 10-attempt rule and presented it as settled for
  429/5xx delivery.
- **Evidence:** Akamai's FAQ says up to 10 attempts within five minutes, while its troubleshooting
  page says data may be lost after three unsuccessful retries.
- **Change:** State both source claims, label the exact per-failure budget `[unverified]`, and retain
  the common no-backup/alert-on-failure conclusion.
- **Expected improvement:** Prevents false confidence in how long failed delivery remains recoverable
  while preserving the operational action.
- **Risk/tradeoff:** The reader receives no single retry count; that uncertainty is more accurate than
  selecting one conflicting vendor statement.

#### Change 2 — preserve the Traffic report lifecycle-date disagreement

- **Problem:** The local text selected 2025-11-06 as an exact date without noting conflicting
  vendor evidence.
- **Evidence:** Akamai's planning changelog gives 2025-11-05; its current Traffic report page gives
  2025-11-06. Both direct users to Traffic by Hostname.
- **Change:** Preserve both dates, label the exact effective day `[unverified]`, and make the
  undisputed retired/current UI distinction explicit while retaining Reporting API v2.
- **Expected improvement:** Avoids false precision without sending operators to a retired UI.
- **Risk/tradeoff:** The reader does not receive one exact day; that detail does not affect the
  current operational action.

### Keep As-Is

Keep one-request versus fleet-wide escalation, Enhanced Debug versus legacy Pragma qualification,
low-latency versus completeness caveats, WAF evidence minimization, property-version diff discipline,
staging-first activation, fast-fallback constraints, and mPulse network/application slicing.

---

## Skill: gcp-ops

### Overall Assessment

**Significant Changes**

### Purpose

Performs read-only, application-side Cloud Run triage during migration, correlates failures with
immutable revisions and logs, preserves credential boundaries, and recommends rather than executes
traffic rollback.

### Findings

- **Routing:** Cloud Run startup, revision, log, and rollback requests are explicit. Seven discovery
  cases cover active incidents and adjacent PCF/log/metric/trace/alert ownership. No description
  change was needed.
- **Instructions:** The four-slot startup/rollback answer shape is strong: evidence, loopback-versus-
  `$PORT` diagnosis, authority, and exact inverse command. The revision paragraph's default-traffic
  shortcut could lead to the wrong deploy/rollback conclusion.
- **Accuracy:** Current Cloud Run documentation supports immutable revisions, startup binding,
  traffic migration, multi-container constraints, direct VPC sizing, domain-mapping Preview status,
  and memory behavior. Existing traffic policies persist; the correction now names that condition.
- **Context:** The entrypoint carries the common triage loop; the Cloud Foundry mapping and local
  inventory remain conditional references. The empty inventory template is useful explicit unknown
  state rather than missing context.
- **References / Assets / Scripts:** No script is needed because project/service/region values and
  guard-approved command shapes must stay explicit. The mapping reference prevents false one-to-one
  migration assumptions.
- **Tools:** Read-only gcloud commands are exact and bounded. Credential-bearing reads, impersonation,
  flag files, and traffic writes are denied or human-only. The corrected text does not grant authority
  to run `--to-latest`.
- **Orchestration:** `stack-profile` supplies the pending runtime boundary; `pcf-ops` owns the source
  runtime; signal skills own backend queries; the human release owner executes traffic changes.
- **Failure Handling:** Loopback binding, cold starts, concurrency, OOM, wrong project/region,
  credential exposure, platform-boundary ambiguity, traffic transition, and incompatible migration
  assumptions remain separate. Existing split persistence is now an explicit failure-prevention rule.
- **Verification:** The focused regression rejects the unconditional latest-revision sentence and
  requires persistent split/assignment behavior, `--no-traffic`, staged `--to-revisions`, and the
  explicit 100% `--to-latest` restoration semantics. No GCP project or service was accessed.
- **Portability:** Revision/change correlation and evidence/authority separation are portable.
  gcloud filters, Cloud Run traffic policy, VPC sizing, and resource constraints are vendor-specific.

### Routing Tests

#### Should trigger

1. “The Cloud Run container failed to listen on PORT; gather the exact read-only evidence.”
2. “List revisions and correlate this 503 increase with the latest Cloud Run deployment.”
3. “Recommend an exact rollback to the previous revision and its inverse command.”

#### Should not trigger

1. “The PCF app is crash-looping” — `pcf-ops` owns the PCF runtime.
2. “Write the Cloud Logging query language expression” — `obs-logs` owns query construction.
3. “Choose Cloud Run or GKE as our landing runtime” — that decision remains pending in
   `stack-profile` and needs human design authority.

#### Boundary cases

1. “Compare a PCF app with its Cloud Run replacement” — use `gcp-ops` for the Cloud Run side and
   mapping traps; obtain PCF evidence from `pcf-ops` without merging authority.
2. “Cloud Run is unhealthy across many projects” — gather project-scoped app evidence here, then
   escalate shared policy/network/platform symptoms to the cloud platform owner.

### Recommended Changes

#### Change 1 — condition latest-revision traffic on the service's existing policy

- **Problem:** “By default traffic routes to the latest healthy revision” omitted persistent splits,
  prior-revision assignments, `--no-traffic`, and the staged-versus-latest routing branch.
- **Evidence:** Cloud Run's traffic documentation says an established allocation persists across
  later deployments and requires an explicit `--to-latest` operation to resume latest tracking.
- **Change:** State the conditional default, name the persistent exceptions, show percentage-based
  `--to-revisions` for a staged assignment, and distinguish `--to-latest` as a 100% switch that also
  restores automatic latest-revision serving for later deployments.
- **Expected improvement:** Prevents an investigator from assuming a newly deployed revision is
  serving traffic or from issuing a rollback/inverse plan against the wrong allocation.
- **Risk/tradeoff:** The paragraph is slightly longer; the extra branch is load-bearing to incident
  diagnosis and release safety.

### Keep As-Is

Keep the four-slot response contract, explicit target flags, `$PORT` loopback comparison, time-bounded
log reads, human-only traffic changes, credential denials, project/platform split, and migration
eligibility map.

---

## Skill: pcf-ops

### Overall Assessment

**Minor Changes**

### Purpose

Performs bounded application-side PCF/TAS triage with `cf` CLI v8 while escalating foundation-side
symptoms and keeping all state-changing or credential-bearing operations human-only.

### Findings

- **Routing:** App status, events, logs, health checks, routes, env groups, and app-side crashes are
  clearly in lane. Platform internals and active incident coordination are explicitly elsewhere.
- **Instructions:** Orient → events → logs → symptom-specific detail is the right low-cost order.
  Target confirmation before app reads and “what changed?” correlation prevent cross-foundation
  mistakes and premature causality.
- **Accuracy:** Current Cloud Foundry documentation supports the CAPI V3 forms, exact HTTP 200 health
  requirement, liveness restart behavior, readiness route-removal behavior, and app-event/log
  semantics. Upstream source supports 90 seconds specifically as the router-to-app backend HTTP
  transport's idle-connection timeout; the reference formerly presented it too generically.
- **Context:** The entrypoint carries common triage and loads only the crash/health, router, or local
  foundation reference required by the symptom.
- **References / Assets / Scripts:** Three references and paired PowerShell/Bash human-run scripts
  are justified. The scripts verify API/org/space before app reads and contain no mutation command.
  The router reference now distinguishes backend pool timing from the separate frontend timeout.
- **Tools:** Guard-safe read shapes are distinct from human-only credential reads and state changes.
  The scripts state that repository bytes must be inspected before execution.
- **Orchestration:** `sre` owns current impact, `pcf-ops` supplies app-runtime evidence, the platform
  team owns BOSH/Ops Manager/Diego/Gorouter/foundation problems, and `gcp-ops` owns the target runtime.
- **Failure Handling:** Wrong target, app crash, health failure, route mismatch, recent restage,
  platform-wide symptoms, credential leakage, and unauthorized restart/scale are explicit stop or
  escalation states.
- **Verification:** The focused regression requires the backend-connection scope, separate frontend
  timeout, and app timeout greater than 90 seconds; its generic-timeout mutant is rejected. Both
  scripts were inspected and parse in their respective shells. No foundation was queried live.
- **Portability:** The evidence-first triage order and authority split are portable. cf commands,
  PCF/TAS concepts, and the guard allowlist are platform/fleet-specific.

### Routing Tests

#### Should trigger

1. “Why is this PCF app crash-looping? Start with status, events, and recent logs.”
2. “Explain whether this HTTP health check failure restarts the instance or removes its route.”
3. “Confirm the current foundation, org, and space before reading this app.”

#### Should not trigger

1. “Investigate the Cloud Run revision” — `gcp-ops` owns the target runtime.
2. “Operate a Diego cell or upgrade the foundation” — the platform team owns it.
3. “Users are impacted right now; assign severity and coordinate response” — `sre` owns the incident.

#### Boundary cases

1. “Every app behind one Gorouter is failing” — capture bounded app-side evidence, then escalate;
   do not operate the router from this skill.
2. “Restart the unhealthy app” — this skill can prepare the exact evidence and recommendation, but
   a human release owner executes the state change after approval.

### Recommended Changes

#### Change 1 — scope the 90-second Gorouter timeout precisely

- **Problem:** “The Gorouter side is a hardcoded 90s” can be read as a universal frontend/backend
  keepalive contract.
- **Evidence:** Upstream source sets 90 seconds on the backend HTTP transport's `IdleConnTimeout`;
  frontend idle timeout is separate and configured by the platform.
- **Change:** Name the backend-connection pool, preserve the app-server `> 90s` race prevention,
  distinguish the frontend timeout, and keep Gorouter settings with the platform team.
- **Expected improvement:** Prevents applying the right app-side remedy for the wrong timer or
  implying authority over a platform-side frontend setting.
- **Risk/tradeoff:** TAS packaging can differ from upstream; the target foundation still needs
  verification before treating an upstream default as deployed fact.

### Keep As-Is

Keep target confirmation, event-first change correlation, bounded logs, status-137/OOM
corroboration, symptom-conditional references, explicit credential denials, state-change separation,
platform escalation, and paired human-run scripts.

---

## Skill: stack-profile

### Overall Assessment

**No Canonical Skill Change; One High-Severity Consumer Correction**

### Purpose

Provides the one canonical statement of current runtime, observability, application/data stack,
model inventory, change/documentation conventions, and app-versus-platform boundaries.

### Findings

- **Routing:** The description correctly triggers before runtime/tool/infrastructure choices and
  broad/current-stack questions. One discovery case exercises the runtime boundary. No description
  change was needed.
- **Instructions:** The entrypoint distinguishes current facts, approved migration, pending decisions,
  owner evidence, and conditional reference loading. The “load every matching row and no others”
  rule is an effective context budget.
- **Accuracy:** The canonical skill already says GCP migration is approved/in progress, Cloud Run
  versus GKE is pending, no self-managed Kubernetes, and migration-scoped managed GCP services are
  in lane. `docs/rules.md` had stale opposite claims and is now corrected to point back here.
- **Context:** Three references isolate observability, application/data, and Copilot model facts.
  The entrypoint holds only cross-cutting boundaries that every consumer must see.
- **References / Assets / Scripts:** No script is needed for owner-recorded stack facts. The
  Copilot model inventory appropriately preserves `[unverified]` status rather than presenting a
  moving picker list as independently verified.
- **Tools:** Loading the profile grants no tool or change authority. Target inspection, validation,
  and owner acceptance remain with the consuming lane.
- **Orchestration:** This is a facts provider, not a workflow owner. Runtime triage goes to PCF/GCP
  skills; platform decisions need human ownership; observability choices load only the relevant
  conditional reference.
- **Failure Handling:** Aspirations cannot become current facts without owner acceptance; pending
  decisions stay pending; host enforcement claims remain host-specific; platform internals are
  escalation boundaries.
- **Verification:** The new regression compares the rules catalog's decision-relevant phrases with
  the canonical GCP boundary and rejects the former contradictory text. The canary/profile tripwire
  remains unchanged.
- **Portability:** The single-source, evidence-state, and progressive-reference pattern is portable.
  The actual stack inventory and host authority details are intentionally team-specific.

### Routing Tests

#### Should trigger

1. “What runtime, databases, observability backends, and CI systems do we use today?”
2. “Should we put this service on GKE or Cloud Run?”
3. “Which backend should I query for traces during the migration?”

#### Should not trigger

1. “Investigate this Cloud Run 503” — `gcp-ops` owns the runtime triage after loading boundary facts.
2. “Write a PromQL error-ratio expression” — `obs-metrics` owns query construction.
3. “Implement a new REST endpoint” — `sde` and the code skills own implementation.

#### Boundary cases

1. “Can we use Secret Manager?” — this skill confirms it is migration-scoped and in lane; the
   consuming engineering skill still owns design and target verification.
2. “Move this workload to GKE” — the profile answers that the decision is pending and GKE must not
   be proposed as settled; it does not make the architecture decision.

### Recommended Changes

#### Change 1 — repair the stale rules-catalog projection

- **Problem:** `docs/rules.md` said GCP was not a target and prohibited all managed cloud services.
- **Evidence:** The canonical `stack-profile` says the approved migration is in progress, lists
  migration-scoped managed GCP services in lane, and keeps only the landing runtime pending.
- **Change:** Update the rules summary to state current PCF runtime, approved/in-progress GCP
  migration, pending landing runtime, no self-managed Kubernetes, and no GKE proposal while pending.
- **Expected improvement:** Consumers no longer receive mutually exclusive runtime/authority rules
  from two live documents.
- **Risk/tradeoff:** The catalog still summarizes a canonical source and can drift again; the focused
  regression now pins the decision-relevant boundary.

### Keep As-Is

Keep the canonical single-source role, current-versus-aspiration distinction, conditional reference
table, no-self-managed-Kubernetes rule, pending-runtime language, app/platform boundaries,
documentation-home rule, and host-specific model distinction.

---

## Architecture Findings

1. **The two-runtime triage split is sound.** `pcf-ops` and `gcp-ops` share evidence discipline but
   differ materially in commands, revision/traffic behavior, credential surfaces, and platform
   boundaries. Merging them would increase context and blur authority.
2. **`stack-profile` is functioning as the canonical fact provider.** The defect was a stale live
   consumer, not missing canonical guidance. A focused consistency regression is the right repair.
3. **Pipeline and signal interpretation remain correctly separate.** `obs-pipeline` proves that
   telemetry crosses boundaries; metric/log/trace skills interpret data after it arrives.
4. **Vendor disagreement is an executable fact.** When current primary pages disagree on retry
   behavior, choosing one number creates false certainty. Preserve both claims and derive only their
   shared safe action.
5. **Upstream-current and target-deployed are distinct.** Dated release evidence helps reproduce the
   audit but does not select a target version or prove a configured preview feature.
6. **A number needs its exact transport scope.** The 90-second backend idle timeout supports an
   app-side keepalive rule; it is not evidence for every Gorouter frontend or backend timer.

## Routing Conflicts

- `[verified]` No description-level routing conflict was found or changed in Batch 5.
- `[verified]` PCF-versus-GCP coexistence is explicit: runtime-specific investigation stays in its
  lane, while comparison tasks use an evidence handoff rather than one skill silently owning both.
- `[verified]` Akamai sustained logs do not transfer log-query construction to `akamai-edge`; it
  supplies fields and edge semantics while `obs-logs` owns the backend dialect.
- `[verified]` `stack-profile` answers “what is allowed/current/pending” but does not absorb the
  implementation or incident task that consumes those facts.

## Shared Resource Opportunities

- Do not centralize `pcf-ops` and `gcp-ops` command tables. Their superficial triage sequence is
  similar, but targets, flags, traffic behavior, credential surfaces, and escalation boundaries are
  different enough that a shared reference would add indirection and failure risk.
- Keep the paired PCF Bash/PowerShell scripts local to `pcf-ops`; no other skill has the same
  target-confirmation and cf-read contract.
- Do not create a shared vendor-lifecycle reference. Lifecycle facts are meaningful only beside the
  operation they gate and would become harder to update correctly if detached.

## Missing Capabilities

No new canonical SRE skill is justified. The observed gaps were incorrect or incomplete facts inside
existing lanes, not missing ownership. GCP platform-boundary ratification and local project inventory
remain owner-evidence gaps, not new capability gaps.

## Standards / Portability Issues

- Portable concepts: evidence-first triage, immutable-change correlation, explicit traffic/rollback
  authority, OTLP pipeline boundaries, OTel resource/naming rules, vendor-disagreement preservation,
  and progressive reference loading.
- Vendor-specific: Alloy components/flags, Cloud Run revisions and traffic, cf CLI/PCF health
  behavior, Akamai diagnostics/property/mPulse surfaces, and their exact lifecycle facts.
- Internal conventions: approved GCP migration, no self-managed Kubernetes, Grafana/Tempo/Mimir/Loki
  targets, human-only production mutation, and the local guard allowlist.
- Shell-specific: the PCF scripts intentionally maintain Bash and PowerShell implementations rather
  than pretending one command surface is portable across hosts.

## Evaluation Gaps

- `obs-pipeline` has no direct discovery scenario. Its boundaries are described well, but alternate
  instrumentation-versus-query phrasing is not measured in the clean-room harness.
- `pcf-ops` appears only as a named alternative in Akamai/GCP deferral cases; a positive app-crash
  or health-check discovery scenario is missing.
- `stack-profile` has one runtime-boundary scenario but no broad stack-inventory or backend-choice
  discovery case.
- Akamai and GCP have strong routing coverage, but none of these scenarios proves current account,
  project, version, permission, or live backend behavior.
- The platform-contract regressions inspect decision-relevant prose and configuration shape. They do
  not parse Alloy, call Cloud Run, query PCF, access Akamai, or prove target adoption.

## Recommended Architectural Changes

### Critical

None.

### High

- **Implemented:** Reconcile `docs/rules.md` with the canonical approved/in-progress GCP migration,
  pending landing-runtime decision, and no-self-managed-Kubernetes boundary.
- **Implemented:** Correct Cloud Run revision guidance so persistent traffic policy and
  `--no-traffic` cannot be mistaken for automatic latest-revision serving.

### Medium

- **Implemented:** Add the documented Alloy Google-auth component, required public-preview flag,
  ADC behavior, and Pre-GA logs qualifier while keeping target adoption unverified.
- **Implemented:** Preserve Akamai's conflicting DataStream retry descriptions and retain only the
  common no-backup/alert-on-failure conclusion.
- **Implemented:** Scope the Gorouter 90-second value to the backend connection pool and distinguish
  the separately configured frontend idle timeout.

### Low

- **Implemented:** Preserve the Akamai Traffic report date disagreement and the current UI replacement.
- **Implemented:** Replace moving Alloy/OTel Java “current” labels with dated review anchors.

## Validation record

- `[verified]` Red first: the initial 5/5 platform-contract tests failed on the untouched claims.
- `[verified]` Red first: the added OTel Java moving-version regression failed before the dated
  wording change.
- `[verified]` Red first after independent review: Cloud Run's missing staged-route branch and the
  unscoped Gorouter timeout both failed their focused tests before correction.
- `[verified]` Green after correction: 8/8 platform-contract tests pass. The eighth test applies ten
  named regressions to the in-memory text; every contract oracle rejects its matching mutant.
- `[verified]` `scripts/check_test_layout.py` passes; the link suite passes 28 tests with one expected
  skip; the direct link checker passes.
- `[verified]` The fleet-validator suite passes 42/42. Direct fleet validation reports only the 30
  expected generated-projection drift paths accumulated across Batches 1–5; regeneration remains
  deliberately deferred until all six canonical batches are committed.
- `[verified]` Offline scenario validation passes all 84 scenarios, and grader tests pass 553/553.
- `[verified]` The PCF Bash script parses with Git for Windows Bash, the PowerShell script parses
  with the Windows PowerShell parser, and `git diff --check` passes.
- `[verified]` Fresh-context independent review initially found two Medium blockers: uncalibrated
  Akamai date disagreement and weak decision-critical mutation oracles. After correction it found no
  remaining Critical, High, or Medium finding and marked the batch commit-ready. Its baseline/current
  replay moved all seven content contracts false → true; it independently observed 8/8 focused tests
  and all ten named mutants rejected.

No routing description changed, so no paid clean-room routing trial is required for this batch. No
GCP project, Cloud Run service, PCF foundation, Akamai account/property, Alloy deployment, or
telemetry backend was accessed or changed.
