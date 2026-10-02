# Group 05: obs-metrics — six-pass audit

Reviewed 2026-10-02 against canonical source `a2d2e57d2de70125dbde002072853e73b788bd8d`; starting audit HEAD `e68e5e4f17a782b4eedc3aa0df30cc550bf40227` contains preceding reports. The initial tree was clean and this bundle matched the frozen source. Recipient/invoking caller: `/root`; human owner: the user. Assignment complete. The parent owns the findings commit and continuing the skills-before-agents review.

**Conclusion:** the skill is suitable for bounded metric interpretation and query construction. Its strongest controls are correct population/unit reasoning, distribution-aware percentiles, rate-before-aggregation, explicit missing-data states, and dialect-specific escaping. No new confirmed defect is established by this review. Four recommendations improve gap-fill policy, Cloud Monitoring portability, authentication-path applicability, and behavioral coverage. Shared query-oracle defects remain relevant and are cross-referenced rather than duplicated.

`[verified]` means inspected current source or the named local evidence; `[sourced]` means retrieved primary documentation/upstream source; `[unverified]` means a target or runtime fact has not been established. The complete five-file bundle was read: `SKILL.md` and `references/{promql,wql,gcp-monitoring,metrics}.md`. There are no bundled executable scripts, templates, or assets. Only this scratch report was written; no platform queries, credentials, installations, service starts, source changes, or paid/native evaluations occurred.

## Pass 1 — suitability, routing, and boundaries

**Sources:** complete entrypoint; `references/metrics.md`; `agents/sre-assistant.md:46-67,183-195`; `agents/observability-engineer.md:218-231`; the Cloud Monitoring discovery scenario and bounded Grafana command-access reference.

[verified] The description separates metric-query work from alert design, dashboard operations, and incident ownership. Supplied-metric interpretation needs no gratuitous live query or new baseline. The task-to-dialect table selects WQL, PromQL, Cloud Monitoring, or the inventory, and requires reading the dialect before constructing the expression. The observing agent loads the skill for metric evidence; the SRE agent remains inside its dispatched slice.

[verified] The inventory is explicitly provisional and records metric type, unit, cadence, population dimensions, backend/tenant, and source links rather than presenting illustrative names as discovered production facts. It accommodates the incumbent PCF/Wavefront path as well as Prometheus/Mimir. Missing instrumentation remains a gap instead of a reason to select a different backend silently.

**Conclusion:** appropriate scope and useful separation between interpretation and investigation. **Gap:** [unverified] actual metric names, units, label cardinalities, tenant identity, emitter contracts, and user access. The discovery case confirms routing intent, not these target facts.

## Pass 2 — technical correctness and current dependencies

**Sources:** `promql.md:15-60,63-111`; `wql.md:38-199`; `gcp-monitoring.md:6-68`; external sources checked 2026-10-02 after local inspection.

[verified] PromQL examples rate each counter before summing, retain `le` for classic-histogram quantiles, and divide matched error/request populations before normalizing to the allowed error fraction. They do not average precomputed quantiles or turn missing denominators into healthy zeroes. Exact-string versus regex encoding is correctly distinguished: the dot in a literal identifier does not need regex syntax; a regex literal requires regex escaping followed by string escaping.

[sourced] Context7's official Prometheus documentation supports the native-histogram query distinction. Its summaries differed on the stability milestone; the actual [Prometheus v3.14.0 changelog](https://github.com/prometheus/prometheus/blob/d7598b71/CHANGELOG.md) resolves that: v3.8 describes native histograms as stable/optional, v3.9 makes the old feature flag a no-op, and v3.14 enables duration expressions by default. Those qualifications in the local reference are supported. They still require deployed-version and flag evidence.

[sourced] GitHits returned the Wavefront documentation snapshot `0492d79`. Its [aggregation specification](https://github.com/wavefrontHQ/docs/blob/0492d79/pages/doc/query_language_aggregate_functions.md#L144) confirms trailing grouping parameters and inner `by` equivalence. The official [histogram merge](https://docs.wavefront.com/hs_merge.html) and [rate](https://docs.wavefront.com/ts_rate.html) references support combining distributions before a percentile and retaining the distinction between positive-change rates and reset gaps. The WQL/PromQL mapping is deliberately approximate, not a claim of identical interpolation or staleness behavior.

[sourced] Context7 did not find an appropriate WQL corpus, so public upstream documentation and direct vendor pages supplied that evidence. The [Mimir 3.2 release notes](https://grafana.com/docs/mimir/latest/release-notes/v3.2/) support query sharding becoming a binary default and the query-planning label change to `engine="querier"`. GitHits supplied a provisional release-document result; the fetched official page supplied the independent versioned contract.

[sourced] Google's [MQL deprecation notice](https://docs.cloud.google.com/stackdriver/docs/deprecations/mql) supports the console restriction and continued operation of existing assets; creation through the API remains possible. “Do not author new MQL” is consequently a team policy, not a claim that every creation mechanism disappeared. The [GA gcloud monitoring reference](https://docs.cloud.google.com/sdk/gcloud/reference/monitoring) still lists dashboards, policies, snoozes, and uptime without a time-series read command. [Cloud Monitoring's compatibility page](https://docs.cloud.google.com/stackdriver/docs/managed-prometheus/promql-differences) substantiates the portability recommendation below.

**Conclusion:** no contradiction established in these refreshed contracts. **Gaps:** [unverified] actual backend versions/features, all post-freeze WQL implementation behavior, tenant limits, client encoding, and target execution. Public documentation is not an observed query result or an entitlement check.

## Pass 3 — authority, trust, and failure handling

**Sources:** `SKILL.md:18-20,39-48,60-80`; `promql.md:95-111`; `wql.md:132-185`; `gcp-monitoring.md:43-55`; `grafana/references/command-access.md:32-90,164-172`; named agent consumers.

[verified] Copied label/tag identifiers are untrusted inputs. The skill prefers exact matching and refuses uncertain encoding rather than broadening a selector. WQL's documented safe literal subset explicitly excludes quotes, backslashes, delimiters, and controls unless a target-validated encoder exists. PromQL explains separate regex, language-string, and client layers. Source identity, UTC window, cadence, and uncertainty belong in the return packet; credentials, personal data, and sensitive high-cardinality values are minimized.

[verified] Query construction grants no dashboard write. The SRE helper path supports bounded Prometheus/Loki query reads after organization and datasource checks; it does not grant arbitrary WQL, SQL, or Cloud Monitoring-plugin queries. The metrics skill correctly tells a lane without the applicable read path to prepare the query for the human. The observability engineer's separate Grafana verification/write rule remains its authority source.

[verified] No-data, stopped-series, late-point, and never-matched-selector cases remain distinct. Mimir rejection IDs route ingestion problems to pipeline work and query-limit problems toward narrowing; defaults are not presented as actual tenant limits. No-data recovery and collector repair are not implied by a successful query rewrite.

**Conclusion:** strong trust and ownership boundaries. **Gap:** [unverified] actual masking, host grants, installed-helper integrity, transport identity, and the receiver's full missing-data lifecycle. These were not exercised by this review.

## Pass 4 — LLM readability, ambiguity, and context cost

**Sources:** all five files, especially the entrypoint's bounded-answer rule, task-to-reference table, and the version/background sections of the dialect references.

[verified] The entrypoint is 5,299 bytes/737 whitespace-delimited words. References are WQL 9,130/1,114; PromQL 6,011/752; Cloud Monitoring 4,653/583; inventory 2,455/344. Total: 27,548 bytes/3,530 words, not a tokenizer measurement. The normal reader need not load every backend. Cloud Monitoring intentionally adds its differences to the common PromQL reference.

[verified] The recurring distinctions are decision-useful: request distribution versus instance statistics, reset-aware counters versus interval deltas, and absent telemetry versus zero. The concrete escaping examples reduce a common model error. The longest reference, WQL, uses a contents list and separate cumulative/delta sections instead of blending incompatible recipes.

**Conclusion:** retain progressive loading and concrete examples. Deletion-first opportunities are to replace the thin Cloud Monitoring compatibility bullet with a short preflight, and replace universal-sounding syncer wording with a conditional heading. Keep exact version facts in one maintained location; do not duplicate release history in the entrypoint. **Gap:** [unverified] native model improvement or savings from further compression. Size alone is not a quality verdict.

## Pass 5 — verification quality and shared limitations

**Sources:** `evals/scenarios/discovery-obs-metrics-cloud-monitoring.yaml`; `evals/README.md:3-14`; `evals/build-scenarios/build-obs-dashboard-write-honours-the-carve-out.yaml`; `evals/test_build_probe.py` query-check coverage found by scoped search; `scripts/test_skill_assets.py`; the committed group-04 Grafana/alerting findings and caller's current DASH-01 evidence.

[verified] The dedicated scenario requests an error ratio, grouped p95, label assumptions, and zero-denominator explanation, but it is a routing case: its actual assertion is successful skill selection. It cannot prove those semantic success criteria. No standalone metrics-dialect behavioral suite was found in the inspected scripts/eval coverage. General asset tests principally protect other shipped examples and structural contracts.

[verified] The shared dashboard build fixture is a stronger integration design: pinned Prometheus produces a classic histogram, native scraping is explicitly disabled, and a populated query is required before the task begins. Its intended check binds a saved panel query to a post-write query. Existing GRA-02/GRA-03 show false acceptance across altered literals and failed/null-only results; root's DASH-01 shows a median can satisfy the nominal p95 check. Those findings limit the strength of this skill's consumer evidence and are not new MET findings. OA-02/OA-03 remain separate alert-rule oracle/fixture issues; AA-01/EL-01 remain their established shared mechanisms.

[verified] Root's frozen-source baseline remains applicable: 1,470 passed, 19 skipped, 1 warning, 2,690 subtests; validation accepted 192 specs/737 expectations. The caller confirmed the source fingerprint still matches. No new executable counterexample was needed for this prose-only bundle.

**Conclusion:** good structural evidence and a meaningful integration design, with named semantic gaps. **Runtime boundary:** Docker CLI exists but its Linux daemon is unavailable and promtool is absent. Neither was started, pulled, or installed. No PromQL/WQL/Monarch query or native trial ran here; the baseline is not live acceptance.

## Pass 6 — adversarial review and prioritized recommendations

### MET-R01 — make the intended duration of WQL zero filling explicit

**Recommendation; Medium priority; high confidence in documented behavior; target applicability [unverified].** Location: `references/wql.md:132-142`; related contract `SKILL.md:43-48`.

The two-argument `default(0, ...)` can fill gaps far beyond a short delayed sample. The [upstream specification](https://github.com/wavefrontHQ/docs/blob/0492d79/pages/doc/ts_default.md#L15) says omission of `timeWindow` can fill through the obsolescence period, up to 28 days, with possible query cost. If only the numerator stops while eligible requests continue, a long synthetic zero can obscure that loss.

This is not a confirmed target defect: the reference already demands verified clean-period emission and warns about concealed telemetry. **Smallest improvement:** for short-gap tolerance, show the documented bounded form and derive its window from observed cadence/lag. If long zero filling is deliberate because clean periods emit nothing, state that policy and prove numerator collection health independently. **Verify:** normal zero, brief delay, sustained numerator loss with denominator traffic, and a selector that never existed; beyond the chosen bound must follow the declared no-data policy.

### MET-R02 — put the important Monarch differences before query construction

**Recommendation; Medium priority; high confidence; [sourced] contract, [unverified] target results.** Location: `references/gcp-monitoring.md:27-29`; common reference `promql.md:79-111`.

A working upstream expression can change meaning on Cloud Monitoring without a conspicuous syntax error. Google's current compatibility page names Prometheus 2.44 parity, unsupported Monarch staleness, rate/irate lookback expansion when shorter than query step, and dropped empty-histogram points instead of NaN. A link used only after misbehavior is easy to miss when constructing a new query.

**Smallest improvement:** replace that bullet with a short preflight naming these decision-changing cases and the exact linked page/check date. Do not duplicate its whole matrix. **Verify:** supplied cases with step larger than lookback, a stopped series, and an empty histogram must retain backend-specific uncertainty rather than assume upstream outputs. Live parity remains a separate target exercise.

### MET-R03 — bind syncer troubleshooting to the discovered datasource path

**Recommendation; Low priority; high confidence; deployment topology [unverified].** Location: `references/gcp-monitoring.md:33-41`.

The [Google guide](https://docs.cloud.google.com/stackdriver/docs/managed-prometheus/query) explicitly prescribes the syncer for its Grafana Prometheus-datasource path, including periodic refresh. That supports the described design. Grafana's separate [Cloud Monitoring datasource](https://grafana.com/docs/grafana/latest/datasources/google-cloud-monitoring/configure/) also supports direct service-account authentication; the guide does not prove which path the team deployed. A console/Grafana mismatch should not trigger a search for a nonexistent syncer.

**Smallest improvement:** title the paragraph for the Prometheus-datasource-plus-syncer case and first record actual datasource type, scoping project, and credential path without secret values. Preserve an already confirmed team default. **Verify:** synthetic syncer and direct-plugin cases select their own bounded auth/data-scope check; neither installs tooling or modifies authentication merely because one view is empty.

### MET-R04 — add semantic negative cases before adding more prompt rules

**Verification recommendation; Medium priority; confidence high; model/backend outcomes [unverified].** Locations: `SKILL.md:22-48,60-68`; the routing scenario above and shared dashboard consumer.

Use a small deterministic set: uneven per-instance request volumes to reject averaged quantiles; one counter resetting while another grows; missing numerator versus zero traffic; and copied identifiers containing a dot, quote, backslash, or case difference. Pair each negative with a valid alternative. Keep native/classic histogram cases distinct. The named dashboard/oracle repairs should land in their existing owners rather than a parallel metrics grader. Where engine execution is unavailable, record a reviewed fixture/expected result as preparation, not a passed query. No new paid campaign is proposed.

**Preserve:** metric contract discovery, honest inventory placeholders, matching population/windows, units, reset handling, histogram representation checks, safe encoding, no-data uncertainty, and human/agent access boundaries. `/root` should commit these six-pass findings with the group-05 batch and continue the parent audit. There is no new confirmed MET defect to fix automatically.

## Central verification

The caller reconciled this report with the group and the [shared verification record](verification.md).
The recorded checks establish their bounded local claims; live-platform and native-model acceptance remain unverified.
