# Group 04: obs-alerting — six-pass audit

Reviewed 2026-10-02 against canonical source `a2d2e57d2de70125dbde002072853e73b788bd8d`; audit HEAD at start `ed7fe6d8ee96055e4128369b142afb2b5db4b80c` contains preceding findings reports. Initial worktree was clean; this bundle had no diff from the frozen source. Recipient/invoking caller: `/root`; human owner: the user. Assignment complete; the parent owns the findings commit and continuing the skills-before-agents audit.

**Conclusion:** useful, well-scoped alert-design guidance with meaningful verification requirements. Confirmed findings are an inclusive-threshold calculator inconsistency, a PromQL grader that accepts an always-active expression, an inaccurate provisioning fixture, and contradictory suppression wording. None establishes a deployed alert defect. Preserve the separation of budget status, current burn, query evidence, notification delivery, and operational authority.

`[verified]` identifies inspected source or named local execution; `[sourced]` identifies current primary documentation/upstream implementation; `[unverified]` identifies remaining runtime or target facts. All six bundle files were read completely. No platform query, notification, cloud write, installation, paid/native evaluation, or canonical edit was performed.

## Pass 1 — fit, routing, and adjacent lanes

**Sources:** complete `skills/obs-alerting/SKILL.md`, four `references/*.md`, and `scripts/error_budget.py`; bounded consumers `agents/observability-engineer.md:23-64,221-231`, `agents/sre-assistant.md:46-67`; `skills/obs-metrics/SKILL.md:15-20,32-48,82-91`; `skills/stack-profile/references/observability-stack.md:8-30`.

[verified] The entrypoint owns alert intent, SLOs, correlation, and synthetics while delegating query construction and Grafana operations. A bounded explanation does not trigger a full implementation workflow. Scheduled work uses freshness instead of forcing request-burn mathematics onto backups and jobs. ThousandEyes supports both existing-result incident reads and separately scoped coverage design; Moogsoft distinguishes correlation from proof of cause.

[verified] Routing has a Splunk design positive and the neighboring `discovery-obs-logs-defers-obs-alerting.yaml` negative. The reliability-to-observability scenario checks the implementation owner. The incumbent stack remains first-class; this skill does not silently replace Splunk or Moogsoft with Prometheus/Grafana.

**Conclusion:** appropriate lane and useful task-shaped reference loading. **Gap:** [unverified] actual test IDs, notification routes, local signature formulas, and owners: reference inventories are placeholders, not operational acceptance evidence.

## Pass 2 — correctness, dependencies, and current contracts

**Sources:** `references/burn-rate.md:8-25,38-52`; `scripts/error_budget.py:51-63,113-146,148-235`; Splunk/Moogsoft/ThousandEyes references in full. Public evidence below was checked 2026-10-02 after local inspection.

[sourced] Google's [SRE Workbook, Table 5-8](https://sre.google/workbook/alerting-on-slos/) supports the three selected pairs and low-traffic qualification. The reference correctly explains that a different horizon changes the estimated budget fractions and that actual request-budget consumption depends on eligible volume. The calculator intentionally retains fixed thresholds; its 28-day budget-status default is disclosed. That policy is not the numeric defect in OA-01.

[sourced] Context7's official Splunk corpus and the current [savedsearches.conf specification](https://help.splunk.com/en/splunk-enterprise/administer/admin-manual/10.4/configuration-file-reference/10.4.1-configuration-file-reference/savedsearches.conf) support the file trigger names, per-result suppression fields, and cross-alert suppression groups. [Scheduling guidance](https://help.splunk.com/en/splunk-enterprise/alert-and-respond/alerting-manual/10.4/create-alerts/alert-scheduling-tips) supports matching cadence/window and allowing for indexing delay. The five-minute example is illustrative, not evidence that a two-minute allowance covers the target's lag.

[sourced] One vendor-document tension remains explicit: the [alert_actions.conf specification](https://help.splunk.com/en/splunk-enterprise/administer/admin-manual/10.4/configuration-file-reference/10.4.1-configuration-file-reference/alert_actions.conf) still lists webhook `enable_allowlist` default false, while [webhook action guidance](https://help.splunk.com/en/splunk-enterprise/alert-and-respond/alerting-manual/10.4/configure-alert-actions/use-a-webhook-alert-action) describes mandatory allowlisting for recent versions. The skill already qualifies target behavior. Effective installed configuration and receiver acceptance remain [unverified]; these public pages cannot establish them.

[sourced] Direct vendor fallback confirms [Moogsoft v9.2 support and release date](https://docs.moogsoft.com/v9/en/moogsoft-releases.html), [Cookbook/Tempus semantics](https://docs.moogsoft.com/v9/en/clustering-algorithm-guide.html), and [maintenance membership behavior](https://docs.moogsoft.com/v9/en/schedule-maintenance-downtime.html). Context7 had no Moogsoft match; direct vendor documentation supplied that contract. The current [ThousandEyes guide](https://docs.thousandeyes.com/product-documentation/getting-started/getting-started-with-the-thousandeyes-api) supports `/v7/tests`, `/v7/agents`, and distinct routing/network/DNS result layers.

**Conclusion:** the main method and refreshed vendor contracts are sound; OA-01/OA-04 isolate concrete inconsistencies. GitHits upstream evidence is used for open-source evaluator/provisioner behavior below, without claiming access to proprietary platform internals. **Gap:** target versions, entitlements, configured behavior, and delivery remain unverified.

## Pass 3 — authority, trust, and failure/recovery

**Sources:** `SKILL.md:17-22,57-75,91-107`; `references/thousandeyes.md:24-38,51-57`; `references/moogsoft.md:20-44`; `agents/observability-engineer.md:66-113,123-129`; `agents/sre-assistant.md:169-190`; `scripts/test_readonly_guard.py:509-517,827-847`.

[verified] Design guidance does not grant live access. Grafana changes inherit the invoked owner's complete resource-specific rule; other external changes remain with the production gate and applying owner. The ThousandEyes automation handoff names the software engineer and human release owner rather than granting this skill a write path. Existing-result SRE reads do not create or run tests.

[verified] Fire/resolve and notification tests are required evidence, with a safe target and no forced production receiver. The skill explicitly places `promtool` execution in the observability lane and scratch storage; the SRE guard denies it and arbitrary calculator execution. Unguarded tool availability does not grant live-change authority. Correlation tuning asks for replay, false merges, missed clusters, and rollback criteria. Sensitive evidence is minimized before handoff.

**Conclusion:** authority and partial-result behavior are appropriately bounded. **Gap:** no actual receiver, recovery transition, maintenance boundary, redaction pipeline, or host enforcement was exercised. A unit-tested condition still does not prove delivery.

## Pass 4 — LLM readability, consistency, and context cost

**Sources:** the entire bundle, especially `SKILL.md:17-48,91-105`, `burn-rate.md:27-43`, and `splunk-alerting.md:46-49,75-77`.

[verified] The entrypoint is 6,643 bytes/953 whitespace words; the five Markdown documents total 21,001 bytes/2,949 words. Including the 10,630-byte Python script gives 31,631 bytes/4,059 words. These are byte/word measurements, not model token counts. The task-to-reference table keeps product details conditional.

[verified] Named units, fixed pair binding, explicit missing evidence, and the cause/hypothesis distinction are clear. The burn reference alternates “meet” and “over,” while calculator output says `>=`; select one boundary policy when repairing OA-01. Splunk's final “per alert” statement conflicts with its earlier suppression-group description (OA-04).

**Conclusion:** improve precision by replacing contradictory sentences, not adding generic safeguards. Preserve progressive loading and the distinction between a useful bounded answer and full readiness proof. **Gap:** no native comparison establishes whether additional compression improves performance.

## Pass 5 — tests and oracle soundness

**Sources:** full `scripts/test_error_budget.py`; `evals/build-scenarios/build-observability-engineer-writes-slo-burn-rules.yaml`; full `evals/oracles/obs-burn-rules/probe_alert_rules.py`; `build-observability-engineer-resumes-after-partial-helper.yaml`; named routing cases; `evals/README.md:3-14,125-139,339-346`.

[verified] Six calculator tests cover exhausted-budget formatting, incompatible units, a positive paired page, missing short window, independent horizon policy, and invalid pair binding. They omit the demonstrated exact-threshold case. The dedicated burn-rule oracle is substantially stronger than string matching: pinned Prometheus evaluates synthetic counter series with separate 500/503 failures, valid 404 traffic, and a failing neighbor. Its cases exercise fast/slow/leak thresholds, spikes, and recovery; shape checks require labels and the published runbook.

[verified] That stronger oracle does not excuse the separate handoff grader's PromQL-to-Python translation (OA-02). The build fixture also misstates its provisioning mechanism (OA-03). Routing success proves selection rather than all the prompt's design criteria. Existing AA-01 identity and EL-01 packet limitations remain cross-cutting where applicable; no duplicate finding is raised.

[verified] Root's unchanged-source baseline remains applicable: Python 3.14.7, 1,470 passed, 19 skipped, 1 warning, 2,690 subtests; validation accepted 192 specs/737 expectations. Fresh root checks reproduced OA-01 and the OA-02 predicate behavior.

**Conclusion:** useful structural and deterministic coverage, with specific false confidence boundaries. **Gap:** the pinned Prometheus/Docker oracle, Grafana provisioning, live delivery, and native agent behavior were not freshly run for this review. Historical “11/11” comments are not current execution evidence.

## Pass 6 — adversarial findings and smallest improvements

### OA-01 — inclusive calculator threshold can be classified below threshold

**Confirmed calculator defect; Medium severity; high confidence; [verified].** Locations: `scripts/error_budget.py:148,190,199,204-207`; policy text `SKILL.md:35-37`; tests `scripts/test_error_budget.py:43-49`.

**Trigger → consequence:** `--slo 99.99 --sli-long 99.856 --sli-short 99.856` mathematically gives 14.4× in both default windows. Binary-float arithmetic yields approximately 14.399999999986678; output prints 14.40× but says below 14.4× instead of the advertised inclusive page. This can mislead a boundary assessment; it does not change deployed rules.

Root ran the actual CLI with Python 3.14.7 `-I -S`: SLIs 99.8559 gave exact decimal 14.41/page; 99.856 gave exact 14.4/no page; 99.8561 gave exact 14.39/no page. All invocations completed normally.

**Smallest fix:** settle inclusive/exclusive wording, then preserve decimal input precision for comparison or use an explicitly bounded numerical strategy. Do not add a broad tolerance that turns genuinely lower burns into pages. **Verify:** exact, just-above, just-below, and mixed-window cases for each pair, with ordinary 99.9% examples retained.

### OA-02 — handoff grader accepts a `bool` expression that keeps healthy samples active

**Confirmed bounded oracle defect; Medium severity; high confidence.** Location: `evals/build-scenarios/build-observability-engineer-resumes-after-partial-helper.yaml:45-51`.

**Trigger → consequence:** an alert uses `(h > bool 0.0144) and (m > bool 0.0144)`, where `h`/`m` are the fixture's actual recording-rule names. The grader removes `bool` and tests Python truth values. It therefore certifies its advertised burn predicate even though the PromQL expression retains matching healthy samples with value zero and becomes firing after the configured hold period.

[verified] Root extracted and executed the exact grader body in a disposable fixture retaining required records, labels, `for`, and runbook: filter AND exit 0; bool AND exit 0; filter OR exit 1. This proves predicate acceptance, not a whole native trial.

[sourced] [PromQL operators](https://prometheus.io/docs/prometheus/latest/querying/operators/) define `bool` values and label-based set intersection. GitHits' Prometheus v3.14.0 snapshot `d7598b71` confirms [retaining zero samples](https://github.com/prometheus/prometheus/blob/d7598b71/promql/engine.go#L3427), [set intersection](https://github.com/prometheus/prometheus/blob/d7598b71/promql/engine.go#L3115), and [creating alert state from returned samples](https://github.com/prometheus/prometheus/blob/d7598b71/rules/alerting.go#L402). No local PromQL engine was run.

**Smallest fix:** reject semantic modifiers outside the scalar oracle's supported subset; do not silently erase them. Prefer the existing pinned evaluator approach for broader syntax. **Verify:** preserve the positive AND and negative OR, reject this bool mutation, and independently check a healthy sustained series remains inactive.

### OA-03 — build fixture conflates Prometheus source with Grafana file provisioning

**Confirmed fixture-fidelity defect; Low severity; high confidence; [verified] local text, [sourced] schema.** Location: `evals/build-scenarios/build-observability-engineer-writes-slo-burn-rules.yaml:8-23,31-32,84-88`.

The task requests native Prometheus rules validated by promtool, while its README says those files are file-provisioned into Grafana-managed alerting. Direct [Grafana file provisioning](https://grafana.com/docs/grafana/latest/alerting/set-up/provision-alerting-resources/file-provisioning/) requires different fields; its [v13.2.0 parser](https://github.com/grafana/grafana/blob/f681b135/pkg/services/provisioning/alerting/rules_types.go#L26) validates interval/folder and title/UID. An obedient answer can pass the Prometheus check while carrying an unsupported deployment assumption.

**Smallest fix:** describe backend-managed evaluation, preserving this oracle, or explicitly name and validate the platform's conversion step. [Grafana import/conversion exists](https://grafana.com/docs/grafana/latest/alerting/alerting-rules/alerting-migration/); it is not the fixture's stated direct file path. **Verify:** the declared evaluator, artifact schema, and checker agree. No failed live reload is claimed.

### OA-04 — Splunk suppression scope is contradicted within one reference

**Confirmed documentation inconsistency; Low severity; high confidence; [verified]/[sourced].** Locations: `references/splunk-alerting.md:46-49,75-77`.

An author using `alert.suppress.group_name` is first told it extends suppression across alerts, then told Splunk throttling is per alert. The current specification confirms same-owner groups suppress other members. The conflict can confuse notification-suppression scope and ownership.

**Smallest fix:** delete the false absolute; state the team's intended Moogsoft correlation ownership separately from Splunk's capability. **Verify:** a same-owner two-alert example identifies shared suppression, while a different-owner control does not; actual installation behavior remains unverified.

**Further recommendation, OA-R01:** prioritize cheap adversarial coverage over new prompt prose: supplied zero/missing denominator and never-successful scheduled-job cases; late-event/duplicate-window Splunk fixtures; Moogsoft false-merge/missed-cluster replay. Preserve explicit gaps until safely exercised. These are coverage proposals, not demonstrated deployed failures.

**Retain:** units and eligible population, paired-window semantics, budget-versus-alert distinction, safe fire/resolve checks, separate delivery evidence, source lineage, healthy synthetic controls, and bounded ownership. `/root` should reconcile the named fresh reproductions, commit group-04 findings, and continue the parent audit. Only this assigned scratch report was written.

## Central verification

The caller reconciled this report with the group and the [shared verification record](verification.md).
The recorded checks establish their bounded local claims; live-platform and native-model acceptance remain unverified.
