# WP04 pinned incident case review

[verified] Selection revision 2 proposes **Scenario-7/21/24/80/102** in
[the manifest](../../evals/manifests/wp04-itbench-five.json): 458 observable assets, 441,911,602
original bytes, original IDs, immutable paths and per-file SHA-256. Every selected root has an
unambiguous binding to an actual observed resource under original metadata. Known-correct,
wrong-root, unavailable and missing-root controls execute against all five real source bindings.
**Zero cases are human-admitted and zero model trials have run.**

[sourced] The source is [ITBench-Lite at d0916b08](https://huggingface.co/datasets/ibm-research/ITBench-Lite/tree/d0916b08ba421ce5e672e9ad68aa947d938dfef0/snapshots/sre/v0.2-B96DF826-4BB2-4B62-97AB-6D84254C53D7),
whose [pinned dataset card](https://huggingface.co/datasets/ibm-research/ITBench-Lite/blob/d0916b08ba421ce5e672e9ad68aa947d938dfef0/README.md)
declares Apache-2.0. Source review screened all 35 GT definitions before model results and inspected
complete observable files for the replacements. Downloads used immutable URLs; upstream code was
not executed. Private sources, hashes, window/trace analyses and prior selection receipts remain
under `.eval-runs/complex-campaigns/wp04-source/` and `wp04-selection-v1/`. Raw telemetry stays out
of Git. None of the exclusions below relies on candidate performance.

| Original ID | Observed discriminator and intrinsic complexity | Remaining limits for human review |
|---|---|---|
| Scenario-7 | [verified] Exact ConfigMap `otel-demo/ConfigMap/flagd-config` changes `paymentFailure` from `off` to `100%` (the recorded variant value is 1), while other flags stay off. All 59 logged checkout HTTP 500 traces pair a checkout attempt with no payment request/success log, in collector window 17:48:33–17:50:13. A same-image payment rollout, successful requests before/after, and unrelated 503 noise require distinguishing configuration, rollout and dependency hypotheses. | Original GT's changed-field example uses `on`/boolean rather than the recorded percentage representation; both originals remain unchanged. Later successful checkout logs coexist with a still-enabled last ConfigMap sample, so recovery mechanism and sustained user recovery remain unknown. Missing payment logs alone do not establish causality; the configuration, transaction-correlated failures and competing rollout evidence must be considered together. |
| Scenario-21 | [verified] Applied StressChaos events match the original `otel-demo-valkey-memory-stress` root filter and target Valkey pods. Later pod state records four restarts and `OOMKilled`; cart connection failures and proxy timeouts connect resource pressure, cache failure, cart and user symptoms across six original edges with branching dependencies. Repeated applied/recovered/forbidden experiment events require temporal reconciliation. | StressChaos objects and exact allocation are absent; event metadata and independent OOM state establish the available mechanism evidence. Injection recovery is not user recovery. Preserve unresolved downstream timing and require sustained user outcomes before closure. |
| Scenario-24 | [verified] Checkout Deployment samples change `KAFKA_ADDR` from `kafka:9092` to `kafka:9999`. Configuration, pod and service layers must be reconciled against generic alerts and the connectivity alternative in case 80. The original root maps exactly to Deployment `checkout`. | GT says checkout continues processing orders; actual records include checkout BackOff. Preserve that source prose inconsistency rather than asserting continued orders; downstream propagation and user outcomes require temporal review. |
| Scenario-80 | [verified] Applied/recovered NetworkChaos events identify checkout/Kafka partition resources and affected pods. Original kind/namespace/filter uniquely map those observed names to the root group. Similar symptoms to case 24 require distinguishing wrong endpoint configuration from connectivity disruption. | NetworkChaos objects are absent. Injection lifecycle is not sustained user recovery or proof of the entire downstream chain. Actual generic/noisy alerts are retained. |
| Scenario-102 | [verified] ResourceQuota state and ReplicaSet `FailedCreate` messages show requested/used/limited memory and quota rejection, connecting namespace policy, controllers, missing pods and service symptoms across six original edges. Namespace `otel-demo` exactly matches the original root. | Root is Namespace, not an invented ResourceQuota alias. Exact downstream user-impact timing and sustained recovery remain unknown. Original overlapping Pod filters remain ambiguous where metadata cannot resolve them; required service-edge bindings are available. |

[verified] Every selected case receives complete selected alert, event and object files. Cases 7 and 21
also receive their **complete application-log TSVs**, without answer-guided excerpting. Other logs,
all traces and metrics are unavailable under `wp04-recorded-observations-v2`. The entire inspected
case 7 trace TSV is excluded because its collector window (17:17:26–17:36:35) predates the observed
configuration/failure window; no selected trace rows are cherry-picked. This is a restricted-observation
adaptation, not a full-snapshot benchmark result.

[verified] All selected observations are released together in a single-response task. Collector
columns and most alert filenames omit a timezone; embedded `Z` timestamps remain UTC. No offset is
invented. Each case records source row counts and collector windows. Public benchmark familiarity
remains uncontrolled. The team's PCF/GCP runtime choices are unchanged by these Kubernetes fixtures.

## Original assessment and local adaptation

[sourced] [ITBench-Evaluations at 14f026fc](https://github.com/itbench-hub/ITBench-Evaluations/tree/14f026fc9cc348c4ecec5ab32714de954c95c1b1)
is an LLM judge. Its [loader](https://github.com/itbench-hub/ITBench-Evaluations/blob/14f026fc9cc348c4ecec5ab32714de954c95c1b1/itbench_evaluations/loader.py)
accepts `<scenario>/<trial>/outputs/agent_output.json`; its
[main prompt](https://github.com/itbench-hub/ITBench-Evaluations/blob/14f026fc9cc348c4ecec5ab32714de954c95c1b1/itbench_evaluations/prompts/main.py)
uses `namespace/Kind/name`, and its
[entity prompt](https://github.com/itbench-hub/ITBench-Evaluations/blob/14f026fc9cc348c4ecec5ab32714de954c95c1b1/itbench_evaluations/prompts/entity_correctness.py)
reads ordered `contributing_factor: true` entities. The loader has no strict generated-response
schema. The adapter's entities/propagations object is an explicit projection into that permissive
contract; an approved judge must still establish its live usability.

[verified] Export retains raw entity names, reasons, ranked hypothesis order and explicit edge
claims. It inserts no GT IDs, aliases, absent reasons or missing edges. Original submissions/reports
remain separate evidence. Original upstream results are imported unchanged; no deterministic score
replaces their semantics. The upstream score remains unknown until approved judging.

[verified] `wp04-exact-entity-edge-v2` reports exact top-ranked root-group membership and directed
edge precision/recall without alias contraction or semantic credit. PASS requires a correct root
and complete exact edge set; a supported root/edge mismatch FAILs. Missing/ambiguous mapping or
malformed/dangling reference edges make the affected metric unavailable, preserving independently
supported dimensions. Empty predictions retain undefined precision as null and measured recall
when reference edges exist. Independent human operational semantics always remain INCONCLUSIVE.
This metric does not reproduce upstream LCS, proximity, reasoning or alias-aware scoring.

[verified] [Evaluator-only bindings](../../evals/manifests/wp04-bindings.json) freeze exact observed
names against original kind/namespace and explicit name or regex metadata. Full resource-name
matches distinguish `frontend` from `frontend-proxy`; unique anchored-prefix matches retain generated chaos
suffixes under the original filters. Unresolved multiple full matches remain ambiguous. No original
filter, group, alias or edge is edited. Bindings and the selection have separate content hashes in
the run plan; they never enter candidate fixture files.

[verified] Independent review exposed four Scenario-102 mappings that treated `ad` inside
`load-generator` as an ad resource. The prior substring fallback was incorrect. All five cases
were rebuilt from hash-bound observations and original GT metadata: 69 entries became 65, with
only those four entries removed. Full matches are preferred; prefix matching uses `re.match`,
never an implicit substring search. The scorer independently validates every consumed binding
against original kind, namespace and name/filter metadata, so supplying the old poisoned map
cannot restore the false PASS. The [repair receipt](wp04-binding-repair.md) retains the red/green
control and current digests. The legitimate ambiguous frontend/proxy Pod mapping remains ambiguous.

## Exclusions and selection corrections

[verified] [The exclusion record](../../evals/manifests/wp04-exclusions.json) preserves source IDs,
rationales and prior case bindings. Case 29 was replaced by 7; case 105 was replaced by 21.

- Scenario-29: `fault.entity.kind` is Service while root kind is JVMChaos; root filter `.*adservice`
  does not match observed `otel-demo-ad-jvm-return-*` names. No inferred alias or root binding.
- Scenario-105: root Deployment filter `product-catalog-.*` does not match actual Deployment name
  `product-catalog`; its fault entity instead identifies a Pod. No root-name correction or alias.
- Scenario-31: [backup provenance](../../evals/manifests/wp04-backup31.json) retains a dangling final
  `frontend-proxy-1` edge and a policy object with `ingress: [{}]`, contrary to the stated deny-all
  fault. It remains excluded; network behavior is not invented from that description.
- Scenario-33: GT has a dangling final proxy edge and an unscheduled-Pod root requiring further
  evidence. It is not substituted for a measurable root through a Deployment alias.
- Scenario-12: actual ConfigMap enables productCatalogFailure/recommendationCacheFailure while
  the fault condition says adServiceHighCpu. Its propagation describes the two other flags;
  the source inconsistency is retained and the case is excluded.
- Scenario-34: full objects/events/logs do not establish its claimed authentication mechanism.
  A mappable Pod name does not supply missing causal evidence.
- Scenario-11: earlier review found a fraud-lag GT versus checkout/ad alert mismatch; not re-admitted.

[verified] The prior draft overstated the number of bound roots: case 105's invalid Deployment
filter was caught by the new every-case binding assertion. It also stated 678 assets where the
actual prior manifest contained 578; original per-file hashes and the 212,710,669-byte total were
correct. No candidate trials, scores or accepted case revisions depended on those draft counts.
Current counts are asserted directly from the manifest, and all five roots now have real bindings.

## Human operational review criteria

The reviewer assesses the complete report against only released observations. These criteria do
not supply a preferred fault name or answer to the candidate:

- Separate competing supported explanations and name an accessible discriminating observation.
  Accept equivalent useful checks and explicit unavailability of a necessary record.
- Preserve collection versus embedded event time, unknown collector timezone, repeated/recovered
  events, onset uncertainty and alert freshness. Avoid interpreting missing telemetry as health.
- Connect initiating mechanism to downstream symptoms with evidence; do not treat every alerted
  service as a root or convert correlation into a claim of proven cause.
- Retain the existing TLC/ITO coordination role and human action authority. Do not claim a live
  read, mutation or actual helper dispatch from supplied records.
- Require sustained user-outcome evidence over a stated window before recovery. Injector recovery,
  a running pod or one quiet alert is insufficient; retain unknown mechanisms and action effects.
- Confirm task feasibility, recognize valid alternatives and retain each source limitation.

[unverified] Human admission reviews these five source-supported proposals and their explicit
limits; it does not supply absent observations or repair rejected cases. Exact candidate/model/host,
read-boundary, spend and judge approval remain separate gates in the [run plan](wp04-operator-runplan.md).
