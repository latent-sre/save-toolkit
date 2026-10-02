# Group 10: service-lifecycle — six-pass audit

Reviewed 2026-10-02 against frozen canonical source `a2d2e57d2de70125dbde002072853e73b788bd8d`; audit HEAD at dispatch was `062d1bfe6748675ee114685307c17c3fdb22abb0`. Recipient/invoking caller: `/root`; human owner: the user. Assignment complete. The parent objective remains the six-pass skills-then-agents audit, three assets per group, with findings committed before advancing.

**Conclusion:** no new confirmed defect was established. This is a useful inventory, planning, and receipt-reconciliation method with particularly good ownership and evidence-freshness rules. Preserve the split between read-only discovery, unapproved drafts, authorized execution by another actor, and independently verified closure. Two recommendations clarify retirement sequencing and the mode-selection table. Producer compatibility and real-service transition acceptance remain explicit gaps; neither is established by the green default suite.

`[verified]` means inspected frozen-source facts or named fresh offline execution; `[sourced]` would mean retrieved primary external evidence; `[unverified]` marks behavior or target facts not established. All four bundle files were read fully: `SKILL.md`, `references/retirement-order.md`, `references/record-transitions.md`, and `context-requirements.yaml`. The audit also inspected directly relevant consumers, the context ADR, tests, scenarios, rubric/calibration, and generated copies. No uncertain public API mechanism required external research. Only this scratch report was written; no canonical changes, producer execution, live operations, installs, paid/native evaluations, or commits occurred.

## Pass 1 — suitability, triggers, and ownership lanes

**Evidence:** complete `SKILL.md`; `agents/reliability-engineer.md:43-55`; `agents/scribe.md:106-139,162-177`; complete `discovery-service-lifecycle-audit.yaml`, `discovery-service-lifecycle-decommission-request.yaml`, and `discovery-reliability-defers-service-lifecycle.yaml` under `evals/scenarios/`.

[verified] Audit is the default for an existing service's readiness. Onboarding and retirement support requested planning even before production approval. Unknown identity constrains discovery to supplied evidence and authorized target-scoped reads; it does not justify inventing an environment or silently selecting production. Unknown consumers and recovery evidence block removal while allowing the inventory needed to resolve them.

[verified] The surfaces cover ownership, runtime, delivery/recovery, telemetry, dashboards, alerts/SLOs, knowledge, dependencies/capacity, and data recovery. Each has a separate audit, onboard, and retire disposition. Workload-appropriate checks and conditional saturation signals avoid turning every service into an identical request-based application. The consumer distinguishes lifecycle coverage from failure-path redesign, implementation, and live incident response.

[verified] Scribe owns the resulting cards, runbooks, indexes, and dispositions; lifecycle does not write those records or load operational-learning to become their author. A receiving role's presence does not authorize it to execute commands or make platform changes.

**Result:** appropriate scope and routing intent. **Gap:** no actual model routing or service inventory was exercised. The table's “Otherwise” header is needlessly ambiguous about when draft preparation applies (LIFE-R02); surrounding instructions establish the intended request boundary.

## Pass 2 — technical and context-contract correctness

**Evidence:** full bundle; `docs/decisions/2026-08-24-sre-operational-context-contract.md` with focus on decisions 4, 8–12 and the acceptance boundary; `scripts/test_service_lifecycle_context.py`; bounded production-gate and operational-learning contracts.

[verified] The sidecar identifies requirements rather than target values: team, service, service lifecycle/qualified owner, environment, and repository resources are required. Deployment and knowledge/runbook/observability/pipeline resources are optional; approval and credential paths are forbidden. Depth and byte budgets are explicit. Optional deployment permits new-service discovery while leaving deployment verification a gap.

[verified] The declared freshness rule is inclusive at 30 days and fails a present deployment with absent/future/older validation date. An explicit current UTC as-of date is required for an actual assessment; a historical date is a reproduction only. Importantly, `record-transitions.md:26-32` separates catalog validation mapped to resolved `lastVerified`, document `last_reviewed`, and execution-backed procedure `last_verified`. A changed deployment can invalidate relevant evidence inside the age window.

[verified] Resolvable retired records remain retired. Catalog owner/state assertions do not establish an accepted transfer, live health, or completed retirement. The required fixture taint and prohibited action selection agree with the ADR's synthetic-only scope. Unsupported required/freshness/forbidden semantics cannot be removed merely to make a resolver succeed.

**Result:** internally coherent consumer contract. The documented producer implementation is an external dependency, not bundled runtime. Its versioned projection and enforcement remain [unverified] here because no selected producer revision ran. P0–P3 priorities, P30D, and human-executor requirements are local policy choices, not universal industry rules.

## Pass 3 — authority, unknown effects, and recovery

**Evidence:** `SKILL.md:14-17,27-39,56,74-98`; complete retirement and record-transition references; `skills/production-change-gate/SKILL.md:14-24,38-59,75-89`; `skills/operational-learning/references/disposition-policy.md:11-18,24-38,56-74`; scribe's knowledge-closeout boundary.

[verified] Live execution belongs to the human release owner or separately approved protected automation, under the exact action gate. The lifecycle method requests no credential-bearing evidence. Its Tier 3 deletion/identity/DNS/access removals require their own recovery evidence and human executor; broad retirement approval cannot authorize undisclosed effects. Onboard/retire readiness requires target, owner, commit, definitions, executor, current gate and, for retirement, dependency/retention/recovery/expiry evidence.

[verified] A dispatch without a durable result stays UNKNOWN and cannot be blindly retried. Each surface has a disposition and owner. The method keeps shared resources visible, preserves historical records as retired, and requires reviewed record readback plus independent retirement verification. A delivered handoff is expressly neither accepted ownership nor closure. The invoking caller keeps tracking unresolved returns.

[verified] Change, remediation, refresh, and retirement each name the accountable owner, record action, and completion/gap condition. Failed remediation, merged code, or a contact-only correction cannot advance operational verification. Unusable cached context cannot silently replace a failed fresh resolution. This is substantive recovery guidance rather than a generic “try again.”

**Result:** strong intended boundaries. LIFE-R01 covers a conditional deployment/quiescence interleaving; existing final verification would still reject resumed work, so no false live completion is demonstrated. **Gap:** no real target, enforcing executor boundary, receipt, restoration, resource transfer, or independent record readback was verified.

## Pass 4 — readability, conflicting cues, and context cost

**Evidence:** full bundle; generator copy behavior at `scripts/generate_platform_adapters.py:525-550`; hashes of the four `.github/skills/service-lifecycle/` copies; bounded scribe handoff wording.

[verified] The bundle is 18,497 bytes, 235 lines, and 2,566 whitespace-separated words: entrypoint 9,023/106/1,281; retirement order 2,465/33/343; record transitions 6,393/69/893; sidecar 616/27/49. These measurements are not model tokens. All generated copies are byte-identical, and relevant canonical files have no diff from the frozen source.

[verified] Progressive loading is sensible: retirement order is required for retirement drafts; record transitions is loaded for changes, remediation, refresh, retirement, and freshness-dependent context use. The surfaces table is dense but presents the same asset across three phases without creating separate inventories. “Up to three” proposed fixes avoids a forced finding quota, while evidence-ranked findings and gaps remain reportable.

The primary readability improvements are to clarify the mode table's third column and consolidate repeated deployment-automation retirement instructions. Keep the three freshness dates and the brief entrypoint pointer: they have distinct operational meanings. Do not create a new lifecycle record schema or duplicate the existing Follow-ups record. The surface-table statement that paging/SLOs retire first is read within observability dependency order, not as authority to remove monitoring before every other retirement step.

**Result:** useful structured guidance with two small simplification opportunities. **Gap:** no comparative model run demonstrates a readability improvement, and the method's no-write boundary remains dependent on its acting lane and host.

## Pass 5 — tests, evaluator soundness, and skipped integration

**Evidence:** complete `scripts/test_service_lifecycle_context.py`; `scripts/test_skill_assets.py:205-224`; `scripts/test_validate_fleet.py:476-512`; both direct lifecycle scenarios; `evals/test_graders.py:830-875`; `evals/rubrics.yaml:172-187`; `evals/rubrics-calibration.yaml:448-554`; the three routing cases listed above.

[verified] Local structural tests check the linked transition table's four nonempty cells per mode, optional deployment with P30D, explicit forbidden authority paths, and required closeout wording. These checks do not prove substantive owner behavior. The producer tests are gated by `SRE_CONTEXT_ROOT` and copy only synthetic catalogs into temporary workspaces. They define useful checks for mirror equality, the inclusive 30-day boundary, 31-day/missing/future dates, explicit as-of, retired records, refresh without operational verification, optional missing deployment, and forbidden/credential fields.

**Fresh root verification:** with `SRE_CONTEXT_ROOT` absent, the verified interpreter ran only `scripts/test_service_lifecycle_context.py` with skip reporting: **2 passed, 11 skipped in 0.02s, exit 0**. Every skip names the missing producer selection. No producer checkout or CLI ran. This result is separate from the frozen full-suite baseline of 1,470 passed, 19 skipped, and 2,690 subtests; 192 specifications/737 expectations were validated centrally. Neither result establishes producer compatibility.

[verified] Direct retirement calibration covers UNKNOWN, refusing retry, Tier 3 ownership, preserved records, unsafe completion claims, raw prompt echoes, and permitted future human plans. The semantic rubric distinguishes effects asserted by any actor from plans/refusals; its calibration contains both sides. The unapproved-draft case allows inventory while rejecting unknown consumers, unclassified shared data, and missing recovery evidence as removal readiness.

The unapproved-draft case uses `exact_fields`, so [EL-01](group-02-eng-ladder.md)'s additional-prose limitation applies; it is not duplicated. Shared [GATE-01](group-08-production-change-gate.md) and [LEARN-01/02](group-06-operational-learning.md) remain their owners' findings. Linked runbook findings do not create a new lifecycle mechanism. Semantic rubric calibration and routing definitions are not native behavior evidence.

**Result:** meaningful structural/decision coverage with honestly skipped integration. **Gap:** there is no executed service-specific four-transition acceptance or live retirement walkthrough in this audit. Existing `record-transitions.md:57-69` already defines that acceptance; keep it pending rather than writing a second framework.

## Pass 6 — counterexamples and ranked improvements

### LIFE-R01 — include work-recreating controllers in the quiescence prerequisite

**Recommendation; Medium priority; high confidence in wording location, conditional consequence.** Locations: `references/retirement-order.md:6-18,23-29`; `SKILL.md:50,58-60`.

**Trigger and consequence:** an independently running deployment, scheduler, or reconciliation path can recreate work during a planned retirement window. The fixed sequence first asks for traffic/dependency exit, then quiescence; it names deployment automation among platform removals and again in delivery/ownership cleanup. A literal draft may defer controlling a known deployment source until after quiescence. Work could resume and force the owner to stop/reconcile, even though final independent checks should prevent claiming retirement complete. No such platform event was observed.

**Smallest improvement:** make the pre-quiescence check explicitly establish that authorized deployment/reconciliation sources cannot introduce new work during the window, with in-flight activity reconciled and rollback capability retained. Any actual freeze remains separately gated. Then consolidate the repeated permanent workflow/environment cleanup into its owning later step. Do not globally destroy automation early, remove shared resources, or stop the telemetry required to detect unexpected consumers.

**Verification:** review a supplied retirement plan with one known in-flight deployment and a retained shared pipeline. The plan must hold quiescence/removal until the reintroduction path is controlled, retain recovery and dependency evidence, and leave shared ownership visible. A quiescent service with already-controlled deployment sources should require no redundant mechanism. This is a sequencing clarification, not a demonstrated authorization bypass or outage.

### LIFE-R02 — make the mode table's draft column explicit

**Recommendation; Low priority; high confidence in ambiguity; model impact unverified.** Location: `SKILL.md:21-34`.

**Trigger and consequence:** the table says Onboard/Retire run when the caller requests that mode, but its “Otherwise” cells describe preparing that mode's draft. Read literally, the fallback can appear to permit a draft when the request condition is absent. The following prose correctly permits requested draft planning without production approval and makes Audit the default; the intended workflow is recoverable, so this is not classified as a confirmed routing defect.

**Smallest improvement:** replace the ambiguous column with “Initial handling after selection” or fold those cells into the existing draft-planning paragraph. Preserve the difference between a request for a mode and approval to execute its plan; missing production approval must not block authorized inventory.

**Verification:** an audit-only request produces an audit, an explicitly requested unapproved retirement produces a draft plus blockers, and a bare unknown target causes only authorized inventory/scope clarification. This is a prose simplification; add a model test only if there is a measured routing failure worth exercising.

**Disposition:** no new confirmed LIFE defect; two recommendations, shared-finding cross-references, and explicit producer/real-service/runtime gaps. Preserve scope-limited discovery, blocked removal with continued inventory, receipt-bound UNKNOWN reconciliation, the three dates, accepted ownership transfers, retired records, and independent closure. `/root` should adjudicate and commit group 10 before beginning the agent batches; completion of this assignment does not complete the parent objective.

## Central verification

The caller reconciled this report with the group and the [shared verification record](verification.md).
The recorded checks establish their bounded local claims; live-platform and native-model acceptance remain unverified.
