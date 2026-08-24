# Full skill audit — Batch 4 of 6

Date: 2026-08-24  
Scope: `obs-alerting`, `obs-dashboards`, `obs-logs`, `obs-metrics`, `obs-traces`  
Baseline commit ID: `90a836d`  
Method: Baseline → Inspect → Research → Change → Validate → Compare

## Executive conclusion

These five skills form a coherent signal-to-decision layer: query construction stays with the
metric/log/trace skills, alert policy stays with `obs-alerting`, and dashboard state stays with
`obs-dashboards`. The bundles already use progressive disclosure well and preserve backend-specific
syntax in references instead of loading it for every observability task.

The audit found six execution-relevant defects:

1. Grafana HTTP examples used curl's default success exit status for 4xx/5xx responses, so a failed
   read or write could continue as though the request succeeded.
2. The alert verification step allowed an always-true rule without requiring a controlled
   non-production rule and test receiver.
3. The error-budget calculator displayed an exactly exhausted budget as `-0.0 min` because its
   state classifier and output formatter handled floating-point tolerance differently.
4. `obs-logs` advertised “build a log alert” as a trigger while the same description assigned alert
   design to `obs-alerting`.
5. The PromQL reference incorrectly used v3.13 as the general duration-expression boundary.
6. The trace reference treated TraceQL metrics and alerting as one vague version-gated surface and
   did not make the current OpenTelemetry-versus-legacy-Tempo attribute disagreement explicit.

The smallest effective corrections are implemented. No agent, delegation edge, production authority,
dependency, schema, or generated projection changed in this batch.

## Method and evidence

### Local baseline

- `[verified]` The baseline contains 30 canonical skill entrypoints totaling 194,161 filesystem
  bytes. The five Batch 4 entrypoints total 32,483 bytes.
- `[verified]` Every file in the five bundles was inspected: 28 files across five entrypoints, 21
  references, and two deterministic scripts. Every supporting resource is linked from its
  entrypoint.
- `[verified]` The existing dashboard checker had 33 passing tests. The error-budget calculator had
  no focused component test despite its exit/output contract.
- `[verified]` Existing discovery regressions target all five skills. `obs-logs` also has a negative
  routing regression that expects full log-derived paging-alert design to route to `obs-alerting`.
- `[verified]` Before the first corrections, three new focused observability contract tests all failed:
  the log description claimed alert design, the forced-alert step lacked a non-production/test-route
  guard, and the Grafana reference lacked HTTP/pipeline failure propagation.
- `[verified]` A focused calculator test reproduced `remaining: -0.0 min` for a 99.9% SLO over 28
  days with exactly 40.32 bad minutes. Four other new calculator contract tests were already green.
- `[verified]` A fourth focused contract test then failed on the stale Prometheus duration-feature
  boundary and passed after the version paragraph was corrected.
- `[verified]` After independent review and the fail-closed sequencing correction, all six
  observability contract tests, all five calculator tests, and all 33 dashboard-hygiene tests pass.

### Current primary documentation via Context7

Context7 was used to establish current documented contracts, not to inspect this private checkout:

- `[sourced]` Grafana documents the app-platform dashboard resource API and states that legacy
  `/api` endpoints remain available but are deprecated from Grafana 13:
  [dashboard API](https://grafana.com/docs/grafana/latest/developers/http_api/dashboard/) and
  [API overview](https://grafana.com/docs/grafana/latest/developers/http_api/apis/).
- `[sourced]` Prometheus documents distinct classic and native histogram queries: classic aggregation
  keeps `le`; native histogram aggregation does not:
  [native histograms](https://prometheus.io/docs/specs/native_histograms/) and
  [`histogram_quantile`](https://prometheus.io/docs/prometheus/latest/querying/functions/).
- `[sourced]` Loki documents stream selectors, left-to-right pipelines, pattern filters, structured
  metadata, metric queries, and `vector(0)` no-data handling:
  [LogQL](https://grafana.com/docs/loki/latest/query/) and
  [metric queries](https://grafana.com/docs/loki/latest/query/metric_queries/).
- `[sourced]` OpenTelemetry documents status as an instrumentation judgment and W3C Trace Context as
  the propagation contract:
  [trace API](https://opentelemetry.io/docs/specs/otel/trace/api/) and
  [HTTP spans](https://opentelemetry.io/docs/specs/semconv/http/http-spans/).

### Current upstream implementation via GitHits

GitHits was kept separate from Context7 and used for exact source/tag evidence:

- `[verified]` Grafana 13.1.4 and 13.2.0 both serve V1 and V2 dashboard kinds. Grafana 13.2.0
  disables scripted dashboards by default and returns HTTP 410; removal is planned for Grafana 14:
  [13.2 toggle](https://github.com/grafana/grafana/blob/f681b1359f6a0b8ecb9f2c49a88ac72b75bde73b/pkg/services/featuremgmt/registry.go#L636-L641)
  and [loader](https://github.com/grafana/grafana/blob/f681b1359f6a0b8ecb9f2c49a88ac72b75bde73b/public/app/features/dashboard/services/DashboardLoaderSrv.ts#L49-L57).
- `[sourced]` Grafana issue #130921 reports bundled plugins missing after 13.2.0. The fix and 13.2.1
  backport merged, but a merged backport is not evidence that a patched artifact was published:
  [issue #130921](https://github.com/grafana/grafana/issues/130921),
  [fix #131033](https://github.com/grafana/grafana/pull/131033), and
  [backport #131037](https://github.com/grafana/grafana/pull/131037).
- `[verified]` Prometheus source confirms `rate()` before aggregation, reset handling, and distinct
  classic/native histogram aggregation:
  [`rate`](https://github.com/prometheus/prometheus/blob/fdfefe22fece4ba3ae8685672e335b175f72f4bd/docs/querying/functions.md#L775-L804)
  and [histogram functions](https://github.com/prometheus/prometheus/blob/fdfefe22fece4ba3ae8685672e335b175f72f4bd/docs/querying/functions.md#L310-L370).
- `[verified]` Prometheus version evidence confirms native histograms stable-but-optional in 3.8 and
  the old flag a no-op in 3.9. It refutes a general “duration expressions v3.13+” boundary: basic
  duration arithmetic arrived in 3.4; newer helpers remained experimental through 3.13 and become
  default in 3.14; extended range selectors began in 3.7 and remain experimental:
  [3.4 changelog](https://github.com/prometheus/prometheus/blob/546b1d242e209ed4228aa01a248dbf3e41e573ea/CHANGELOG.md#L3-L9),
  [3.8 changelog](https://github.com/prometheus/prometheus/blob/e44ed351cdf0181f9fde56ba096f4d949f9e295d/CHANGELOG.md#L5-L12),
  [3.9 changelog](https://github.com/prometheus/prometheus/blob/cd875bd8c9211d7606981223d59ab3adf73432f2/CHANGELOG.md#L3-L5), and
  [3.14 changelog](https://github.com/prometheus/prometheus/blob/d7598b7141418fa35be2b5ec5d0fefb634199610/CHANGELOG.md#L3-L8).
- `[verified]` Current Loki source confirms selector/pipeline ordering, `|>`/`!>` pattern filters,
  and the difference between log-range `rate`, unwrapped `rate`, and `rate_counter`:
  [log queries](https://github.com/grafana/loki/blob/e6ba27c6dd75955372610f414b83ed3311a11d18/docs/sources/query/log_queries/_index.md#L12-L28)
  and [metric queries](https://github.com/grafana/loki/blob/e6ba27c6dd75955372610f414b83ed3311a11d18/docs/sources/query/metric_queries.md#L35-L101).
- `[verified]` Current OpenTelemetry names are `http.request.method` and
  `http.response.status_code`; Tempo's current examples still include legacy `span.http.status_code`:
  [OTel HTTP attributes](https://github.com/open-telemetry/semantic-conventions/blob/384d66161cb18704c729645fa8136a148df9571c/docs/http/http-spans.md#L151-L160)
  and [Tempo example](https://github.com/grafana/tempo/blob/ad33aa8fafc41a4ea58519f7b7a88b1aa1383224/docs/sources/tempo/traceql/construct-traceql-queries.md#L28-L39).
- `[verified]` TraceQL metrics are GA from Tempo 3.0, but metrics-query alerting remains experimental,
  has a 24-hour query window, and is unavailable as a Grafana Managed Alerts source:
  [Tempo 3.0 notes](https://github.com/grafana/tempo/blob/ad33aa8fafc41a4ea58519f7b7a88b1aa1383224/docs/sources/tempo/release-notes/v3-0.md#L84-L90)
  and [limitations](https://github.com/grafana/tempo/blob/ad33aa8fafc41a4ea58519f7b7a88b1aa1383224/docs/sources/tempo/solutions-with-traces/solve-problems-metrics-queries.md#L30-L34).

### Provenance disagreements retained

- Context7 returned a historical OpenTelemetry OTEP when asked about current HTTP 4xx status. The
  audit therefore used the current normative semantic-conventions source through GitHits. The local
  rule—server 4xx normally Unset, client 4xx Error, 5xx Error—matches that source.
- Tempo's current README still calls TraceQL metrics experimental, while the newer Tempo 3.0 release
  notes declare the query feature GA. This report follows the release note for query lifecycle and
  retains the explicit exception that alerting remains experimental.
- Grafana's open issue is evidence of the 13.2.0 packaging regression, not evidence that a merged
  fix has failed. Conversely, merged fix/backport PRs do not prove a release artifact exists.

---

## Skill: obs-alerting

### Overall Assessment

**Minor Changes**

### Purpose

Turns user-visible symptoms into reviewable SLIs, SLOs, budget decisions, paging rules,
correlation, and synthetics while keeping metric/log query construction with the signal skills.

### Findings

- **Routing:** The description clearly owns SLOs, noisy alerts, paging policy, correlation, and
  synthetics. It defers query construction to `obs-metrics`/`obs-logs`, dashboards to
  `obs-dashboards`, and active impact to `sre`. A regression covers Splunk saved-search design.
- **Instructions:** The SLI denominator, unit discipline, paired-window rule, no-data rule, and
  fire/resolve definition of done are explicit. The forced-alert example needed a safety qualifier:
  an always-true rule can notify a real production route even when the expression itself is harmless.
- **Accuracy:** The error-budget arithmetic and standard 14.4x/6x/1x paired-window method are
  technically sound. The calculator's state used a tolerance but its output did not, exposing a
  floating-point `-0.0` value at exact exhaustion.
- **Context:** The 7.6 KB entrypoint contains the backend-independent alert contract. Five vendor or
  method references load only for matching work; the deterministic calculator avoids asking an LLM
  to perform repeated arithmetic.
- **References / Assets / Scripts:** The burn-rate, Grafana, Splunk, Moogsoft, and ThousandEyes
  references are appropriately conditional. `error_budget.py` is stdlib-only and now has a focused
  CLI regression suite.
- **Tools:** Validation names syntax checks, rule tests, notification delivery, runbook resolution,
  and distinct guarded/unguarded execution authority. A human or authorized lane runs the script.
- **Orchestration:** Query evidence comes from the signal skill; `observability-engineer` owns the
  reviewed alert; `sre` owns active impact; the human service owner owns budget policy. No extra
  delegation or workflow graph is needed.
- **Failure Handling:** Mixed SLI units, invalid numeric values, illegal window pairs, one-window
  severity, no-data, untested delivery, and unresolved recovery are explicit failure states. The
  forced-notification path now stays non-production/test-only.
- **Verification:** Five calculator CLI tests cover exact exhaustion, unit mixing, dual-window page,
  one-window non-verdict, and illegal pair. The routing regression covers Splunk alert design.
- **Portability:** SLI/SLO and multi-window concepts are portable. Grafana, Splunk, Moogsoft, and
  ThousandEyes configuration is vendor-specific and isolated in named references.

### Routing Tests

#### Should trigger

1. “Define a 99.9% availability SLO and multi-window burn-rate alerts for checkout.”
2. “This Grafana page is noisy; redesign the paging condition and no-data behavior.”
3. “Design an outside-in ThousandEyes synthetic check for the critical payment journey.”

#### Should not trigger

1. “Write the exact PromQL for checkout p99 latency” — `obs-metrics` owns the query.
2. “Checkout is failing for users right now; investigate” — `sre` owns active impact.
3. “Add an SLO row to the Grafana checkout dashboard” — `obs-dashboards` owns the dashboard.

#### Boundary cases

1. “Build a log-derived paging alert” — `obs-alerting` owns the rule/window/route/runbook;
   `obs-logs` supplies the verified query evidence.
2. “Alert when the nightly backup has not succeeded” — this skill owns freshness alert policy even
   though there is no request stream or burn-rate denominator.

### Recommended Changes

#### Change 1 — constrain forced notification tests

- **Problem:** An always-true rule could satisfy “force the condition” while reaching a production
  receiver.
- **Evidence:** The Grafana reference already required a controlled non-production rule, but the
  always-loaded entrypoint omitted that constraint.
- **Change:** Require a controlled non-production rule routed only to a test contact point, and
  explicitly prohibit forcing a production receiver.
- **Expected improvement:** Preserves end-to-end delivery evidence without creating an avoidable
  production page.
- **Risk/tradeoff:** A production route still needs separate evidence before release; the safe test
  proves configuration flow, not every production integration.

#### Change 2 — align calculator display with its numeric tolerance

- **Problem:** Exact exhaustion displayed `remaining: -0.0 min`.
- **Evidence:** The pre-change CLI output reproduced it while correctly classifying the state as
  `EXHAUSTED`; the focused test failed on that mismatch.
- **Change:** Clamp values within the existing budget-relative tolerance to positive zero before
  formatting, and add five CLI contract tests.
- **Expected improvement:** Machine and human consumers receive a consistent state/value pair.
- **Risk/tradeoff:** Only values below the existing classification tolerance are clamped; material
  negative remaining budget is unchanged.

### Keep As-Is

Keep the unit separation, paired-window rule, staleness treatment for scheduled work, fire-and-resolve
verification, runbook requirement, and progressive vendor references. Each prevents a distinct alert
quality or operational-safety defect.

---

## Skill: obs-dashboards

### Overall Assessment

**Significant Changes**

### Purpose

Designs and directly applies Grafana 13 operations dashboards under a narrow dashboard-only write
rule with schema pinning, concurrency protection, query/read-back verification, and durable version
history.

### Findings

- **Routing:** Dashboard build/edit/export is clear; product UI charts defer to `frontend-craft`,
  alert rules to `obs-alerting`, and active incidents to `sre`. One discovery regression exercises a
  live dashboard edit.
- **Instructions:** The read → export → author → validate → diff → write → verify → record loop has
  named progress and termination criteria. The entrypoint is dense because it carries the live-write
  authority boundary; API mechanics stay in references.
- **Accuracy:** Current Grafana source confirms the V1/V2 surface, 13.x legacy-API deprecation,
  scripted-dashboard 13.2 behavior, and the 13.2.0 bundled-plugin regression. Version-bound QA
  observations remain labeled rather than generalized to Grafana Cloud or a later minor.
- **Context:** The 10.7 KB entrypoint loads only for dashboard tasks. The 32 KB HTTP reference and
  30 KB JSON reference are large, but each is loaded only for an API/model task where the detail
  prevents silent schema or concurrency loss. Splitting them further would fragment one execution
  path without demonstrated context benefit.
- **References / Assets / Scripts:** Six references separate HTTP operations, JSON schema, tooling,
  user workflows, and local inventory. The stdlib checker intentionally refuses V2 rather than
  silently inspecting zero panels.
- **Tools:** The live-write path checks permissions, target, schema, diff, concurrency token, query
  results, optional render, and version history. The HTTP examples previously used `curl -sS`, which
  returns zero on 4xx/5xx. The first correction added `pipefail`, but independent review proved that
  it did not stop a later write after a separate body-builder failed.
- **Orchestration:** `observability-engineer` performs the narrow dashboard/folder write;
  `obs-metrics` owns query construction and `scribe` owns new runbook content. The handoffs are
  necessary and carry exact identifiers/evidence rather than whole model context.
- **Failure Handling:** Schema mismatch, missing permissions, stale versions, managed dashboards,
  unavailable rendering, and wrong query data are explicit. HTTP transport failure and
  prerequisite-to-write fall-through were the remaining silent-continuation gaps.
- **Verification:** All 33 dashboard-hygiene tests remain green. The execution-contract tests prove
  every executable Bash curl call uses the fail-closed wrapper, pipelines enable `pipefail`, and
  every POST/PUT body is produced or validated by a success-gated prerequisite. Named fall-through
  mutations for create, legacy create, import, update, legacy update, and rollback are rejected.
- **Portability:** Dashboard content rules are broadly portable, but the API versions, RBAC scopes,
  annotations, and live-write authority are Grafana/internal conventions. Bash arrays are explicitly
  translated to literal flags for PowerShell/POSIX `sh` users.

### Routing Tests

#### Should trigger

1. “Add a p99 latency panel to checkout-health and apply it through the Grafana 13 API.”
2. “Export this Grafana dashboard and explain why its stored schema is V1 rather than V2.”
3. “Design a 3 a.m.-usable operations dashboard for the payment service.”

#### Should not trigger

1. “Add a Recharts component to the customer admin UI” — `frontend-craft` owns product UI.
2. “Design the paging threshold and contact point” — `obs-alerting` owns alert policy.
3. “The dashboard shows checkout down; find the cause now” — `sre` owns the incident.

#### Boundary cases

1. “Import a community dashboard” — use this skill for the controlled Grafana import, but treat the
   downloaded JSON as untrusted data and rebind instance identifiers.
2. “Change one panel on a file-provisioned dashboard” — discover ownership here, then stop; the
   provisioning source must change through its owning workflow.

### Recommended Changes

#### Change 1 — propagate every Grafana HTTP failure

- **Problem:** `curl -sS` exits zero on HTTP 4xx/5xx. A permission error, conflict, or invalid request
  could be parsed, saved, or followed by verification as though transport succeeded.
- **Evidence:** The reference's own failure table treats those statuses as stop/reconcile states,
  but none of its calls enabled curl failure propagation. The initial contract test failed.
  Independent review then reproduced `set -o pipefail; false; printf WRITE_RAN`, which still prints
  and exits zero, and found the same fall-through in create, update, and rollback recipes.
- **Change:** Define one Bash transport array using `--fail-with-body --show-error --silent`, enable
  `pipefail`, use the array for every HTTP example, and chain each request-body builder or validator
  directly to its POST/PUT with `&&`. Keep expected non-zero `diff` output outside that chain.
- **Expected improvement:** HTTP errors retain their diagnostic body but cannot masquerade as
  successful JSON or silently continue into a write/rollback step.
- **Risk/tradeoff:** `--fail-with-body` requires a modern curl; PowerShell and POSIX `sh` users must
  pass the flags literally because they do not support Bash arrays. The reference now says so.

### Keep As-Is

Keep the dashboard-only authority exception, read-before-write rule, stored-version probe,
`resourceVersion`/`dashboard.version` concurrency protection, `overwrite: false`, status stripping,
query and optional visual verification, durable save message, and refusal to claim V2 validation from
a V1-only checker. These are high-signal safeguards, not removable ceremony.

---

## Skill: obs-logs

### Overall Assessment

**Minor Changes**

### Purpose

Builds bounded, reproducible log queries and timelines across Splunk, Loki, and Cloud Logging while
keeping alert policy and active-incident ownership elsewhere.

### Findings

- **Routing:** The body consistently assigns alert design to `obs-alerting`, but the description
  listed “build a log alert” as a positive trigger. That contradicted the existing negative routing
  regression and could reduce precision.
- **Instructions:** Start-narrow, complete-bucket, stable-dimension, one-request correlation, and
  before/after-rate instructions are concise and operationally meaningful.
- **Accuracy:** Current Loki source supports the reference's selector, parser, structured-metadata,
  pattern-filter, metric-query, and no-data semantics. The phrase “upstream current: 3.7.x” was
  unnecessary drift-prone context; feature use already depends on the deployed target.
- **Context:** The 4.4 KB entrypoint carries the backend-neutral investigation shape. Four references
  isolate SPL, LogQL, Cloud Logging, and local inventory.
- **References / Assets / Scripts:** Backend references contain query shapes, escaping, limits, and
  evidence labels; no deterministic transformation justifies adding a script.
- **Tools:** The skill requires exact query, tenant/index, absolute UTC window, field assumptions,
  and smallest necessary evidence. It does not grant live write authority.
- **Orchestration:** Recurring query/correlation work goes to `observability-engineer`; active impact
  goes to `sre`; missing identifiers become an `sde` telemetry-gap handoff. It explicitly does not
  load another skill itself.
- **Failure Handling:** Wrong tenant, missing field extraction, incomplete buckets, unsafe identifiers,
  parser errors, query limits, and missing logs remain distinct. It stops instead of broadening an
  unencodable identifier.
- **Verification:** Existing discovery cases cover Cloud Logging activation and deferral of full
  paging-alert design. The changed description uses the existing deferral regression as its focused
  after-change routing check.
- **Portability:** The investigation shape is portable. SPL, LogQL, and Cloud Logging syntax stays in
  vendor-specific references; live inventory placeholders remain `[unverified]`.

### Routing Tests

#### Should trigger

1. “Search checkout logs for a 5xx spike over this UTC window.”
2. “Write a LogQL query that follows this validated trace ID across two services.”
3. “Compare the checkout error rate in equal windows before and after this deploy.”

#### Should not trigger

1. “Build a paging alert with throttling, notification ownership, and a runbook” — `obs-alerting`.
2. “Define the p95 request-latency metric query” — `obs-metrics`.
3. “Checkout is failing now; coordinate the incident” — `sre`.

#### Boundary cases

1. “Write the log expression used by a future alert” — this skill owns the query and evidence only;
   `obs-alerting` owns evaluation, suppression, notification, and runbook policy.
2. “No logs match this request ID” — validate tenant/window/field/escaping and report absence causes;
   never widen arbitrary untrusted input into a broad search.

### Recommended Changes

#### Change 1 — remove alert design from positive triggers

- **Problem:** The description simultaneously triggered on “build a log alert” and said
  `obs-alerting` owns alert design.
- **Evidence:** The existing `discovery-obs-logs-defers-obs-alerting` regression expects that exact
  class of request not to fire `obs-logs`.
- **Change:** Replace the conflicting trigger with “write a log query,” preserving query-construction
  recall while making the alert boundary consistent.
- **Expected improvement:** Better routing precision for full alert-design requests without losing
  log-query requests.
- **Risk/tradeoff:** Compound requests may need `obs-alerting` to obtain a query-evidence handoff from
  this lane; that is the existing ownership model.

#### Change 2 — remove the upstream-current Loki version label

- **Problem:** A moving “current: 3.7.x” label adds drift without changing the instruction.
- **Evidence:** The safe behavior is already to confirm the deployed Loki version before using
  version-gated syntax; current primary/upstream evidence establishes syntax, not target adoption.
- **Change:** Keep the version gate and source date; remove the moving current-version parenthetical.
- **Expected improvement:** Less stale context and no false implication that upstream current equals
  the deployed version.
- **Risk/tradeoff:** The reader must inspect release documentation if it needs a minimum version for a
  specific feature; that lookup was already required.

### Keep As-Is

Keep complete-bucket timelines, rate-not-count deploy comparisons, stable-dimension breakdowns,
identifier escaping, evidence minimization, and dialect-first progressive loading. These rules directly
prevent biased baselines, false causal claims, matcher widening, and unnecessary telemetry exposure.

---

## Skill: obs-metrics

### Overall Assessment

**Minor Changes**

### Purpose

Constructs and interprets metric queries across Wavefront, Prometheus/Mimir, and Cloud Monitoring,
with correct distribution, counter, denominator, missing-data, and target-validation semantics.

### Findings

- **Routing:** Metric-query construction is explicit; alert policy stays with `obs-alerting`, logs
  with `obs-logs`, and active incident work with `sre` through the owning agent lane.
- **Instructions:** Distribution-versus-point-value latency, rate-before-aggregation, matched
  numerator/denominator, and four distinct missing-data states are concise and technically important.
- **Accuracy:** Context7 and GitHits confirm classic/native histogram differences, rate/reset behavior,
  aggregation ordering, missing-vector omission, staleness, and `absent()` semantics. The reference's
  general “duration expressions v3.13+” cutoff was incorrect and is now replaced with the actual
  3.4/3.7/3.14 boundaries. Target-specific metric names, flags, versions, and tenant limits remain
  explicitly unverified.
- **Context:** The 4.7 KB entrypoint carries only backend-neutral semantics. Four references isolate
  WQL, PromQL/Mimir, Cloud Monitoring, and local inventory.
- **References / Assets / Scripts:** Query work requires target inspection and semantic judgment; no
  new script or schema would improve reliability. Detailed version/limit material is correctly
  deferred to references.
- **Tools:** The skill tells the model what to inspect before writing a selector and what result
  metadata to retain. It does not imply permission to change metric pipelines.
- **Orchestration:** Exact query/window/value/no-data evidence goes to `observability-engineer` for
  alert or dashboard follow-up; pipeline defects go to `obs-pipeline`. The division is sufficient.
- **Failure Handling:** Zero denominator, nonexistent series, stale series, wrong label, mixed
  histogram representation, resets, and backend limits are not collapsed into “zero” or “no data.”
- **Verification:** A Cloud Monitoring discovery regression checks PromQL ratio/histogram shapes and
  zero-denominator language. A focused static regression pins the duration/extended-selector version
  boundaries. Live metric/label existence remains target-bound and unverified.
- **Portability:** Metric semantics are portable. WQL, PromQL/Mimir, and Cloud Monitoring syntax and
  lifecycle notes remain clearly vendor-specific.

### Routing Tests

#### Should trigger

1. “Write PromQL for checkout error ratio and p95 latency grouped by service.”
2. “Explain whether these per-instance quantiles can produce a fleet p99.”
3. “Why did this Mimir selector return no series after the deploy?”

#### Should not trigger

1. “Choose the page threshold and contact point for this error ratio” — `obs-alerting`.
2. “Build a Grafana panel around this already-verified query” — `obs-dashboards`.
3. “Fix the Alloy remote-write pipeline” — `obs-pipeline`.

#### Boundary cases

1. “Write the PromQL portion of a future alert” — this skill owns the expression and no-data
   evidence; it does not own the paging policy.
2. “Native histogram p95 returns no data” — confirm whether the target exports native or classic
   representation before changing the query or declaring missing telemetry.

### Recommended Changes

#### Change 1 — correct the PromQL duration-feature timeline

- **Problem:** The reference described duration expressions inside range selectors as v3.13+.
- **Evidence:** Upstream changelogs place basic duration arithmetic in v3.4, extended range selectors
  in v3.7, experimental helper evolution through v3.13, and default duration expressions in v3.14.
- **Change:** State those actual boundaries, retain the experimental flag for extended selectors,
  and preserve the rule to confirm deployed version/flags before shared use.
- **Expected improvement:** Prevents rejecting valid older syntax or assuming 3.13 makes the newer
  helper surface generally available.
- **Risk/tradeoff:** More version detail adds a small maintenance surface; the dates/versions are
  load-bearing because they determine parse behavior.

### Keep As-Is

Keep the percentile/distribution distinction, rate-before-sum rule, same-population ratio contract,
zero-denominator caution, four-way missing-data taxonomy, untrusted matcher handling, exact evidence
packet, and backend-specific progressive references.

---

## Skill: obs-traces

### Overall Assessment

**Minor Changes**

### Purpose

Interprets one sampled request's causal path and latency allocation across Tempo/TraceQL or Cloud
Trace, then correlates it with logs without overstating prevalence, status, or absence.

### Findings

- **Routing:** Single-request path/latency questions are clear; instrumentation and export changes
  defer to `obs-pipeline`, population trends to metrics, and active incident ownership to `sre`.
- **Instructions:** Critical-path reading, nested-duration non-additivity, normal-trace comparison,
  status/protocol separation, and sampling/retention caveats are strong.
- **Accuracy:** Current OTel confirms server 4xx normally Unset, client 4xx Error, 5xx Error, stable
  HTTP attribute names, and W3C propagation. Local examples use current attributes, but current Tempo
  docs still show legacy names; that disagreement is now explicit. TraceQL metrics-query lifecycle
  and alerting lifecycle are now separated.
- **Context:** The 5.0 KB entrypoint holds the backend-neutral waterfall method. Three references
  isolate TraceQL, Cloud Trace, and OpenTelemetry semantics.
- **References / Assets / Scripts:** Queries depend on deployed attributes, tenant, retention, and
  backend version; examples and interpretation belong in references. No deterministic script would
  remove that judgment safely.
- **Tools:** Direct trace-ID lookup, constrained search, comparison selection, and evidence recording
  are clear. Query syntax never grants instrumentation-change authority.
- **Orchestration:** Missing propagation/instrumentation/export becomes an `obs-pipeline` finding;
  logs provide request-to-trace mapping; `sre` receives time-bounded evidence for active impact.
- **Failure Handling:** Missing trace/span/log may mean sampling, retention, size limits, propagation,
  export, or instrumentation. The skill refuses to turn absence or a long span into causal proof.
- **Verification:** A Cloud Trace discovery regression checks critical-path interpretation,
  non-additivity, normal comparison, sampling, and UTC bounding. TraceQL syntax examples carry
  source labels and target-unverified status.
- **Portability:** The trace model, span kinds, W3C Trace Context, and OTel semantics are portable.
  TraceQL and Cloud Trace query surfaces are vendor-specific and conditionally loaded.

### Routing Tests

#### Should trigger

1. “Follow this validated trace ID across checkout and payments and find the critical path.”
2. “Compare this slow Tempo trace with a known-normal trace without double-counting child spans.”
3. “Explain why the Cloud Trace span status is Unset even though the server returned 404.”

#### Should not trigger

1. “Instrument checkout with OpenTelemetry and configure export” — `obs-pipeline`.
2. “Measure how common this latency is across all requests” — `obs-metrics` or trace-metrics analysis.
3. “The service is currently down; coordinate investigation” — `sre`.

#### Boundary cases

1. “Tempo docs use `http.status_code`, but our service emits `http.response.status_code`” — use this
   skill to inventory/interpret observed attributes; do not rewrite instrumentation here.
2. “Create an alert from a TraceQL metrics query” — query capability is GA on supported Tempo, but
   alerting remains experimental and constrained; route alert policy to `obs-alerting` and pipeline
   feasibility to the platform owner.

### Recommended Changes

#### Change 1 — document the OTel/Tempo attribute disagreement

- **Problem:** A reader could copy Tempo's legacy `span.http.status_code` example and treat it as the
  current OpenTelemetry instrumentation contract.
- **Evidence:** Current OTel source marks `http.response.status_code` stable and the old name
  deprecated; current Tempo documentation still demonstrates the old attribute.
- **Change:** State that the Tempo example is valid only for telemetry emitting the legacy
  convention and require target-field inventory.
- **Expected improvement:** Empty queries prompt schema inspection rather than a false “no errors”
  conclusion or an unnecessary instrumentation rewrite.
- **Risk/tradeoff:** The reference retains both names, adding one short branch; this is necessary
  during migration coexistence.

#### Change 2 — separate TraceQL query GA from alerting experiment status

- **Problem:** “All are version-gated” blurred the maturity of TraceQL metrics queries and alerting.
- **Evidence:** Tempo 3.0 release notes declare metrics queries GA; current limitations keep alerting
  experimental, cap the window at 24 hours, and exclude Grafana Managed Alerts.
- **Change:** Name the GA boundary and the alerting-specific constraints while keeping target-version
  validation.
- **Expected improvement:** Prevents both underusing supported queries and overpromising production
  alert capability.
- **Risk/tradeoff:** Lifecycle facts can drift; the reference includes source/date and still requires
  checking the deployed version.

### Keep As-Is

Keep critical-path rather than duration-summing analysis, known-normal comparison, span-status versus
protocol-status separation, W3C trace-ID validation, sampling/retention caveats, evidence minimization,
and instrumentation ownership with `obs-pipeline`.

---

## Architecture Findings

1. **The signal/policy/presentation split is sound.** Metrics/logs/traces build evidence;
   `obs-alerting` owns paging policy; `obs-dashboards` owns presentation and its narrow live write.
2. **Progressive disclosure is working.** Backend syntax and version-bound details are not duplicated
   across the five entrypoints; each entrypoint routes to the one relevant reference.
3. **Negative evidence is consistently modeled.** Missing logs, metrics, traces, dashboard search
   results, and alert data each have multiple causes and are never automatically converted to healthy
   zero.
4. **Live-state operations need transport and sequencing failure as part of the contract.** The
   dashboard loop had rich application-level failure handling but missed curl's HTTP exit semantics
   and allowed separate builders to fall through to writes. Every prerequisite must succeed before
   response interpretation or mutation.
5. **Current-versus-target version is a recurring boundary.** Upstream feature status is useful only
   when kept separate from the deployed Grafana/Loki/Prometheus/Tempo version and target evidence.

## Routing Conflicts

- `[fixed]` `obs-logs` listed “build a log alert” as a positive trigger while assigning alert design
  to `obs-alerting`. It now triggers on “write a log query”; the existing negative regression remains
  the executable boundary.
- `[verified]` “Write the query used by an alert” legitimately starts in the metric/log skill, while
  “design the rule/window/route/runbook” belongs to alerting. This is a handoff boundary, not a reason
  to merge the skills.
- `[verified]` Dashboard panels that contain PromQL do not transfer query semantics to
  `obs-dashboards`; it consumes verified query evidence and owns the model/write.

## Shared Resource Opportunities

- Do not centralize the signal skills' evidence-packet language yet. The repeated fields are similar,
  but each backend needs distinct assumptions (labels/fields/sampling/tenant), and a shared reference
  would add a load without removing current ambiguity.
- The fail-closed curl wrapper is a candidate reusable pattern only if another live-write skill
  repeats the same Bash HTTP flow. One occurrence does not justify a shared utility.
- Keep the two deterministic scripts local to their owning skills. Error-budget arithmetic and
  dashboard JSON hygiene do not share an input/output contract.

## Missing Capabilities

No new SRE capability gap was established in this batch. Capacity, performance, pipeline,
incident, readiness, and change-safety work already has a neighboring lane. Broader live-backend
coverage is an evaluation gap, not evidence for another skill.

## Standards / Portability Issues

- Portable concepts: Agent Skills discovery/body/reference structure, SLI/SLO arithmetic, RED/USE,
  critical-path trace reading, evidence labels, and read/verify/report loops.
- Vendor-specific: Grafana API versions/RBAC/annotations, SPL/LogQL/TraceQL/WQL, Cloud Logging/Trace,
  Moogsoft, ThousandEyes, and their target versions. These remain explicitly isolated.
- Internal convention: Grafana is the dashboard record and `observability-engineer` has a narrow
  dashboard/folder write exception. This is not a portable Agent Skills authority guarantee.
- Harness-specific: Bash arrays and `pipefail` are not PowerShell or POSIX `sh` syntax. The reference
  supplies a literal-flag fallback and does not present the Bash form as universal.

## Evaluation Gaps

- Only `obs-logs` has both a positive backend case and a negative alert-design routing case. The
  other signal skills have one primary discovery scenario each; recall across alternate phrasings is
  not measured.
- Grafana API behavior is backed by prior QA evidence at 13.1.4, not a live 13.2 trial in this batch.
  Every `[verified: QA]` label correctly demotes after upgrade.
- PromQL, LogQL, and TraceQL examples have strong primary/source evidence, but most target metric,
  label, tenant, and version assumptions remain unverified until executed against the deployed stack.
- `dashboard_hygiene.py` deliberately refuses V2. V2 validation depends on the external Grafana
  linter or a live round trip; the refusal is safer than silent partial coverage.
- The new calculator suite validates CLI semantics but not every numeric boundary or locale. It is a
  focused regression, not exhaustive property testing.

## Recommended Architectural Changes

### Critical

None.

### High

- **Implemented:** Make all Grafana dashboard HTTP examples fail closed on 4xx/5xx, preserve
  pipeline failures, and success-gate every prepared request body before create, import, update, or
  rollback writes.

### Medium

- **Implemented:** Constrain forced alert delivery to a controlled non-production rule and test
  contact point.
- **Implemented:** Remove full alert design from `obs-logs` positive triggers while preserving
  log-query recall.
- **Implemented:** Align error-budget numeric output with its exhaustion tolerance and add focused
  CLI verification.
- **Implemented:** Correct PromQL duration/extended-selector version boundaries while retaining
  target-version and feature-flag checks.
- **Implemented:** Separate TraceQL metrics-query GA status from experimental alerting constraints
  and preserve the OTel/Tempo attribute disagreement.

### Low

- **Implemented:** Remove the moving “upstream current” Loki version label; retain target-version
  validation and current source dates.

## Validation record

- `[verified]` Red first: the first 3/3 observability contract tests failed before their changes; the
  later PromQL version-boundary test also failed before its correction.
- `[verified]` Red first: exact exhaustion failed on `remaining: -0.0 min` while four other calculator
  contracts passed.
- `[verified]` Independent review initially rejected the batch: `pipefail` did not prevent separate
  create/update/rollback builders from falling through to writes. The strengthened oracle failed on
  those paths and then exposed the previously untested import-body path before its validation gate
  was added.
- `[verified]` Green after correction: 6/6 observability contract tests, including six named
  prerequisite-to-write fall-through mutations.
- `[verified]` Fresh-context re-review found no remaining Critical, High, or Medium finding and
  marked the corrected batch commit-ready; an additional raw-curl mutation and removal of the
  rollback-read gate were also rejected.
- `[verified]` Green after change: 5/5 calculator CLI tests.
- `[verified]` Green after change: 33/33 dashboard-hygiene tests.
- `[verified]` `scripts/check_test_layout.py` passes with both new executable unittest files.
- `[verified]` Every Bash fence in the modified Grafana HTTP reference passes `bash -n` under Git
  for Windows Bash.
- `[verified]` `git diff --check` passes.
- `[verified]` The direct fleet validator reports the expected generated-projection drift from
  canonical edits in Batches 1–4. Projections remain deliberately unregenerated until all six
  canonical batches are committed; its 42 focused validator tests pass.
- `[verified]` Focused clean-room routing run `20260824T082901Z-fa4341d6` passed 3/3 trials on
  `claude-opus-5[1m]` through Claude Code 2.1.241. Every trial invoked `save-toolkit:obs-alerting`
  and not `obs-logs`; total reported cost `$1.5993115`.

No broad or agent-target routing campaign was run. No target Grafana, Prometheus/Mimir, Loki, Tempo,
Cloud Logging, Cloud Monitoring, Cloud Trace, Splunk, Moogsoft, or ThousandEyes system was changed.
